"""
MIGRACAO DE PRODUCAO — hierarquia Administrador > Coordenador > Equipe >
Instrutor > Aluno.

MAPEAMENTO DE PAPEIS (o ponto delicado):
Os numeros 2 e 3 MUDARAM de significado entre o schema antigo e o novo:

    valor | ANTIGO       | NOVO
    ------+--------------+-------------
      1   | ADMIN        | ADMIN
      2   | GESTOR       | COORDENADOR
      3   | SUPERVISOR   | INSTRUTOR
      4   | ALUNO        | ALUNO

Portanto NAO se pode migrar "as cegas": e preciso remapear a semantica.
Decisao do ARQUITETO:
    gestor@gsi.ebd      -> COORDENADOR (dono do ambiente)
    coordenador@gsi.ebd -> INSTRUTOR   (vinculado ao coordenador)
    alunos              -> instrutor_id = coordenador@gsi.ebd (ja era o supervisor deles)
    egarabini#hotmail   -> permanece SEM vinculo

IDEMPOTENTE e com TRAVA DE BACKUP.

Uso:
    python migrar_producao.py --conferir   (padrao, so leitura)
    python migrar_producao.py --aplicar
"""
from __future__ import annotations

import argparse
import os

from sqlalchemy import inspect, text

BACKUP_ESPERADO = r"C:\Projetos\EM_ESTUDO\gsi_ebd-backup-producao-2026-10-06-COMPLETO.json"

COORDENADOR_EMAIL = "gestor@gsi.ebd"
INSTRUTOR_EMAIL = "coordenador@gsi.ebd"
ORFAO_EMAIL = "egarabini#hotmail.com"

COLUNAS_NOVAS = {
    "user": ["coordenador_id", "instrutor_id", "equipe_id", "ambiente_id"],
    "progress": ["ambiente_id"], "userresponse": ["ambiente_id"],
    "studyassignment": ["ambiente_id"], "notification": ["ambiente_id"],
    "subscription": ["ambiente_id"], "paymenthistory": ["ambiente_id"],
    "turma": ["ambiente_id", "equipe_id", "instrutor_id"],
}
COLUNAS_LEGADAS = {"user": ["gestor_id", "supervisor_id"], "turma": ["gestor_id"]}
FK_REF = {"ambiente_id": "ambiente", "coordenador_id": "user",
          "instrutor_id": "user", "equipe_id": "equipe"}


def _checar_backup() -> None:
    if not os.path.exists(BACKUP_ESPERADO):
        raise SystemExit("MIGRACAO ABORTADA: backup ausente em\n  " + BACKUP_ESPERADO)
    tam = os.path.getsize(BACKUP_ESPERADO)
    if tam < 10_000:
        raise SystemExit(f"MIGRACAO ABORTADA: backup suspeito ({tam} bytes)")
    print(f"backup verificado: {tam/1024:.1f} KB\n")


def _cols(insp, t):
    return {c["name"] for c in insp.get_columns(t)}


def planejar(con, insp) -> list[str]:
    acoes, tab = [], set(insp.get_table_names())
    for t, cs in COLUNAS_NOVAS.items():
        if t not in tab:
            continue
        ex = _cols(insp, t)
        acoes += [f"ADD {t}.{c}" for c in cs if c not in ex]
    for t, cs in COLUNAS_LEGADAS.items():
        ex = _cols(insp, t)
        acoes += [f"DROP {t}.{c} (legado)" for c in cs if c in ex]
    for t in ("ambiente", "ambienteestudo", "equipe", "equipeinstrutor"):
        if t not in tab:
            acoes.append(f"CRIAR TABELA {t}")
    if "ambiente" in tab:
        n = con.execute(text("SELECT COUNT(*) FROM ambiente")).scalar()
        if n == 0:
            acoes.append(f"CRIAR ambiente de {COORDENADOR_EMAIL}")
    ex = _cols(insp, "user")
    if "coordenador_id" in ex:
        r = con.execute(text('SELECT role FROM "user" WHERE email = :e'),
                        {"e": COORDENADOR_EMAIL}).first()
        if r and r[0] != 2:
            acoes.append(f"PROMOVER {COORDENADOR_EMAIL} a COORDENADOR (role 2)")
        r = con.execute(text('SELECT role, coordenador_id FROM "user" WHERE email = :e'),
                        {"e": INSTRUTOR_EMAIL}).first()
        if r and (r[0] != 3 or r[1] is None):
            acoes.append(f"TORNAR {INSTRUTOR_EMAIL} INSTRUTOR (role 3) vinculado ao coordenador")
        n = con.execute(text(
            'SELECT COUNT(*) FROM "user" WHERE role = 4 AND instrutor_id IS NULL AND email <> :o'),
            {"o": ORFAO_EMAIL}).scalar()
        if n:
            acoes.append(f"VINCULAR {n} aluno(s) a {INSTRUTOR_EMAIL}")
    else:
        acoes.append(f"PROMOVER {COORDENADOR_EMAIL} a COORDENADOR (role 2)")
        acoes.append(f"TORNAR {INSTRUTOR_EMAIL} INSTRUTOR (role 3)")
        n = con.execute(text(
            'SELECT COUNT(*) FROM "user" WHERE role = 4 AND email <> :o'),
            {"o": ORFAO_EMAIL}).scalar()
        if n:
            acoes.append(f"VINCULAR {n} aluno(s) a {INSTRUTOR_EMAIL}")
    acoes.append("MANTER " + ORFAO_EMAIL + " SEM vinculo (decisao do arquiteto)")
    return acoes


def aplicar(con, insp) -> None:
    def log(m):
        print("   ", m)
    tab = set(insp.get_table_names())

    # 1. tabelas ausentes
    if "ambiente" not in tab or "equipe" not in tab:
        from sqlmodel import SQLModel
        import gsi_ebd.models  # noqa: F401
        for t in ("ambiente", "ambienteestudo", "equipe", "equipeinstrutor"):
            if t in SQLModel.metadata.tables and t not in tab:
                SQLModel.metadata.tables[t].create(con)
                log(f"tabela {t} criada")
        insp = inspect(con)

    # 2. colunas novas
    for t, cs in COLUNAS_NOVAS.items():
        if t not in set(insp.get_table_names()):
            continue
        for c in cs:
            if c not in _cols(insp, t):
                ref = FK_REF.get(c)
                fk = f' REFERENCES "{ref}"(id)' if ref and ref in set(insp.get_table_names()) else ""
                con.execute(text(f'ALTER TABLE "{t}" ADD COLUMN {c} INTEGER{fk}'))
                con.execute(text(f'CREATE INDEX IF NOT EXISTS ix_{t}_{c} ON "{t}"({c})'))
                log(f"ADD {t}.{c}")
        insp = inspect(con)

    # 3. colunas legadas
    for t, cs in COLUNAS_LEGADAS.items():
        for c in cs:
            if c in _cols(insp, t):
                con.execute(text(f'ALTER TABLE "{t}" DROP COLUMN {c}'))
                log(f"DROP {t}.{c}")
        insp = inspect(con)

    # 4. coordenador: role=2, topo da cadeia, dono do ambiente
    coord = con.execute(text('SELECT id, nome_completo FROM "user" WHERE email = :e'),
                        {"e": COORDENADOR_EMAIL}).first()
    if not coord:
        raise SystemExit(f"Coordenador {COORDENADOR_EMAIL} nao encontrado — abortando")
    coord_id, coord_nome = coord
    con.execute(text('UPDATE "user" SET role = 2, coordenador_id = NULL WHERE id = :i'),
                {"i": coord_id})
    log(f"{COORDENADOR_EMAIL} (id={coord_id}) -> COORDENADOR")

    amb = con.execute(text("SELECT id FROM ambiente WHERE coordenador_id = :c"),
                      {"c": coord_id}).scalar()
    if not amb:
        amb = con.execute(text(
            "INSERT INTO ambiente (nome, slug, coordenador_id, logo_url, cor_primaria, "
            "cor_secundaria, tipografia, landing_titulo, landing_subtitulo, landing_ativa, "
            "is_active, created_at) VALUES (:n,'demo',:c,'','#7c3aed','#4f46e5','Inter',"
            "'Estudos Biblicos Dirigidos','Aprenda a Palavra com acompanhamento.',false,true,NOW()) "
            "RETURNING id"), {"n": f"Ambiente de {coord_nome}", "c": coord_id}).scalar()
        log(f"ambiente id={amb} criado")
    con.execute(text('UPDATE "user" SET ambiente_id = :a WHERE id = :c'), {"a": amb, "c": coord_id})

    eq = con.execute(text("SELECT id FROM equipe WHERE coordenador_id = :c"),
                     {"c": coord_id}).scalar()
    if not eq:
        eq = con.execute(text(
            "INSERT INTO equipe (nome, descricao, ambiente_id, coordenador_id, nivel, is_active, "
            "created_at) VALUES (:n,'Instrutores do ambiente.',:a,:c,'basico',true,NOW()) "
            "RETURNING id"), {"n": f"Equipe {coord_nome.split()[0]}", "a": amb, "c": coord_id}).scalar()
        log(f"equipe id={eq} criada")

    # 5. instrutor: quem era "coordenador" (role 3 antigo) vira INSTRUTOR do coordenador
    inst = con.execute(text('SELECT id, nome_completo FROM "user" WHERE email = :e'),
                       {"e": INSTRUTOR_EMAIL}).first()
    if inst:
        inst_id = inst[0]
        con.execute(text(
            'UPDATE "user" SET role = 3, coordenador_id = :c, ambiente_id = :a, equipe_id = :e '
            'WHERE id = :i'), {"c": coord_id, "a": amb, "e": eq, "i": inst_id})
        log(f"{INSTRUTOR_EMAIL} (id={inst_id}) -> INSTRUTOR do coordenador")
        vinculo = con.execute(text(
            "SELECT id FROM equipeinstrutor WHERE equipe_id = :e AND instrutor_id = :i"),
            {"e": eq, "i": inst_id}).first()
        if not vinculo:
            con.execute(text("INSERT INTO equipeinstrutor (equipe_id, instrutor_id, is_active, "
                             "created_at) VALUES (:e,:i,true,NOW())"), {"e": eq, "i": inst_id})
            log("instrutor vinculado a equipe")
    else:
        inst_id = None
        log(f"AVISO: {INSTRUTOR_EMAIL} nao existe — alunos ficarao sem instrutor")

    # 6. alunos -> instrutor (dentro do ambiente)
    if inst_id:
        r = con.execute(text(
            'UPDATE "user" SET instrutor_id = :i, coordenador_id = :c, ambiente_id = :a '
            'WHERE role = 4 AND email <> :o'),
            {"i": inst_id, "c": coord_id, "a": amb, "o": ORFAO_EMAIL})
        log(f"{r.rowcount} aluno(s) vinculados ao instrutor {inst_id}")
        con.execute(text(
            'UPDATE "user" SET instrutor_id = NULL, coordenador_id = NULL, ambiente_id = :a '
            'WHERE email = :o'), {"a": amb, "o": ORFAO_EMAIL})
        log(f"{ORFAO_EMAIL} mantido sem vinculo de instrutor")

    # 7. turma
    if "turma" in set(inspect(con).get_table_names()):
        ct = _cols(inspect(con), "turma")
        if "instrutor_id" in ct and inst_id:
            con.execute(text("UPDATE turma SET instrutor_id = :i WHERE instrutor_id IS NULL"),
                        {"i": inst_id})
        if "ambiente_id" in ct:
            con.execute(text("UPDATE turma SET ambiente_id = :a WHERE ambiente_id IS NULL"), {"a": amb})
        if "equipe_id" in ct:
            con.execute(text("UPDATE turma SET equipe_id = :e WHERE equipe_id IS NULL"), {"e": eq})
        log("turma atualizada")

    con.execute(text("UPDATE alembic_version SET version_num = 'c3b4d5e6f7a8'"))
    log("alembic_version -> c3b4d5e6f7a8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    from rxconfig import config
    from sqlalchemy import create_engine
    _checar_backup()
    print(f"ALVO: {str(config.db_url).split('@')[-1]}\n")
    eng = create_engine(str(config.db_url))
    insp = inspect(eng)

    with eng.connect() as con:
        acoes = planejar(con, insp)
        print(f"=== ACOES ({len(acoes)}) ===")
        for a in acoes:
            print("   -", a)
        if not args.aplicar:
            print("\n(dry-run: nada alterado. Use --aplicar.)")
            return 0
        print("\n=== APLICANDO ===")
        con.rollback()                      # encerra a transacao implicita das leituras
        try:
            aplicar(con, insp)
            con.commit()
            print("\n>>> MIGRACAO CONCLUIDA")
        except Exception:
            con.rollback()
            print("\n!!! ERRO — ROLLBACK EXECUTADO, NADA FOI ALTERADO")
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
