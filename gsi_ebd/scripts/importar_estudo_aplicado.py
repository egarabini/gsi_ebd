"""Importa o ESTUDO aplicavel a partir do que ja esta no banco.

A fonte da carga e o BANCO, nao o markdown: os `Study`/`StudyVersion` ja contem o
conteudo e as questoes que o aluno consome. O importador so LE essas tabelas
(RF09) e nunca escreve nelas.

Pre-condicao dura (design §4): a OBRA precisa existir. Sem ela o importador
ABORTA sem criar nada — falhar e melhor do que criar capitulos sem origem.

Idempotente por (estudo, ordem) e por (capitulo do estudo, capitulo da obra).

Uso:
    python -m gsi_ebd.scripts.importar_estudo_aplicado            # confere
    python -m gsi_ebd.scripts.importar_estudo_aplicado --apply     # grava
    python -m gsi_ebd.scripts.importar_estudo_aplicado --apply --autoteste
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import func  # noqa: E402
# `select` do SQLMODEL, nao o do SQLAlchemy: o do SQLAlchemy devolve Row, e
# `row.id` estoura. O mesmo defeito existe no importador da obra (re-execucao).
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from gsi_ebd.models import (  # noqa: E402
    Estudo,
    EstudoCapitulo,
    EstudoCapituloOrigem,
    Obra,
    ObraCapitulo,
    Study,
    StudyStatus,
    StudyVersion,
)

# Os capitulos do livro seguem "Cap. NN — ...". Os 5 estudos de exemplo nao seguem,
# e ficam de fora por decisao do ARQUITECT (intent §8.2).
RE_CAPITULO = re.compile(r"^Cap\.\s*(\d+)\b", re.IGNORECASE)

TITULO_OBRA_PADRAO = "Doutrinas Cristãs"
TITULO_ESTUDO_PADRAO = "Doutrinas Cristãs — Estudo Dirigido"


class PreCondicaoError(RuntimeError):
    """Falta o que o importador precisa para gravar sem inventar dado."""


# ── funcoes puras (testaveis sem banco) ─────────────────────────────────────

def ordem_do_titulo(titulo: str) -> int | None:
    """`Cap. 07 — A Criacao` -> 7. None quando o titulo nao segue o padrao."""
    achado = RE_CAPITULO.search((titulo or "").strip())
    return int(achado.group(1)) if achado else None


def escolher_versao(versoes):
    """A versao de maior numero; empate resolve pela mais recente.

    Sem versao -> None: o capitulo entra vazio e o caso e reportado, em vez de o
    importador inventar conteudo.
    """
    validas = [v for v in versoes if v is not None]
    if not validas:
        return None
    return max(validas, key=lambda v: (v.version or 0, v.created_at or datetime.min))


def selecionar_estudos(estudos):
    """Separa os capitulos do livro (com `Cap. NN`) dos demais estudos.

    Devolve (selecionados ordenados por ordem, ignorados).
    """
    selecionados, ignorados = [], []
    for estudo in estudos:
        ordem = ordem_do_titulo(estudo.title)
        if ordem is None:
            ignorados.append(estudo)
        else:
            selecionados.append((ordem, estudo))
    return sorted(selecionados, key=lambda par: par[0]), ignorados


# ── banco ──────────────────────────────────────────────────────────────────

def contar(session: Session, modelo) -> int:
    return int(session.execute(select(func.count()).select_from(modelo)).scalar_one())


def resolver_obra(session: Session, titulo: str) -> Obra:
    """A pre-condicao dura. Levanta ANTES de qualquer escrita."""
    obra = session.exec(select(Obra).where(Obra.titulo == titulo)).first()
    if obra is not None:
        return obra
    existentes = ", ".join(o.titulo for o in session.exec(select(Obra)).all()) or "(nenhuma)"
    raise PreCondicaoError(
        f"obra '{titulo}' nao encontrada. Obras no banco: {existentes}. "
        "Rode o importador da obra (Fase 1) antes — NADA foi criado."
    )


def capitulos_da_obra(session: Session, obra: Obra) -> dict[int, ObraCapitulo]:
    return {
        cap.ordem: cap
        for cap in session.exec(
            select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)
        ).all()
    }


def versoes_por_estudo(session: Session, estudos) -> dict[int, StudyVersion | None]:
    saida: dict[int, StudyVersion | None] = {}
    for _, estudo in estudos:
        versoes = session.exec(
            select(StudyVersion).where(StudyVersion.study_id == estudo.id)
        ).all()
        saida[estudo.id] = escolher_versao(versoes)
    return saida


def conferir(session: Session, titulo_obra: str) -> dict:
    """Somente leitura: prova a pre-condicao e mostra o plano da carga."""
    obra = resolver_obra(session, titulo_obra)
    capitulos = capitulos_da_obra(session, obra)
    if not capitulos:
        raise PreCondicaoError(
            f"a obra '{obra.titulo}' existe mas nao tem capitulos — NADA foi criado."
        )
    estudos = session.exec(select(Study).order_by(Study.id)).all()
    selecionados, ignorados = selecionar_estudos(estudos)
    if not selecionados:
        raise PreCondicaoError(
            "nenhum Study com titulo 'Cap. NN' no banco — NADA foi criado."
        )
    return {
        "obra": obra.titulo,
        "capitulos_da_obra": len(capitulos),
        "selecionados": len(selecionados),
        "ignorados": [s.title for s in ignorados],
        "sem_capitulo_de_obra": [ordem for ordem, _ in selecionados if ordem not in capitulos],
    }


def gravar(session: Session, titulo_estudo: str, titulo_obra: str) -> dict:
    """Idempotente. A primeira coisa que faz e provar a pre-condicao."""
    obra = resolver_obra(session, titulo_obra)
    capitulos_obra = capitulos_da_obra(session, obra)
    if not capitulos_obra:
        raise PreCondicaoError(
            f"a obra '{obra.titulo}' existe mas nao tem capitulos — NADA foi criado."
        )

    estudo = session.exec(select(Estudo).where(Estudo.titulo == titulo_estudo)).first()
    if estudo is not None and estudo.obra_id != obra.id:
        raise PreCondicaoError(
            f"ja existe um estudo '{titulo_estudo}' ligado a outra obra (id {estudo.obra_id})."
        )
    if estudo is None:
        estudo = Estudo(
            obra_id=obra.id,
            titulo=titulo_estudo,
            descricao=f"Estudo aplicavel gerado da obra {obra.titulo}.",
            created_at=datetime.utcnow(),
        )
        session.add(estudo)
        session.flush()

    estudos = session.exec(select(Study).order_by(Study.id)).all()
    selecionados, ignorados = selecionar_estudos(estudos)
    if not selecionados:
        raise PreCondicaoError(
            "nenhum Study com titulo 'Cap. NN' no banco — NADA foi criado."
        )
    versoes = versoes_por_estudo(session, selecionados)

    novos = atualizados = origens_novas = sem_origem = sem_versao = 0
    for ordem, study in selecionados:
        versao = versoes.get(study.id)
        if versao is None:
            sem_versao += 1
        conteudo = versao.content_md if versao else ""
        questoes = versao.questions_json if versao else "[]"

        cap = session.exec(
            select(EstudoCapitulo).where(
                EstudoCapitulo.estudo_id == estudo.id,
                EstudoCapitulo.ordem == ordem,
            )
        ).first()
        if cap is None:
            cap = EstudoCapitulo(
                estudo_id=estudo.id,
                ordem=ordem,
                titulo=study.title,
                conteudo_md=conteudo,
                questions_json=questoes,
                # Nasce em rascunho: nada fica disponivel sem aprovacao (ADR-011).
                status=StudyStatus.RASCUNHO.value,
                created_at=datetime.utcnow(),
            )
            session.add(cap)
            session.flush()
            novos += 1
        else:
            mudou = (
                cap.titulo != study.title
                or cap.conteudo_md != conteudo
                or cap.questions_json != questoes
            )
            if mudou:
                cap.titulo = study.title
                cap.conteudo_md = conteudo
                cap.questions_json = questoes
                session.add(cap)
                atualizados += 1

        capitulo_obra = capitulos_obra.get(ordem)
        if capitulo_obra is None:
            sem_origem += 1
            continue
        existe = session.exec(
            select(EstudoCapituloOrigem).where(
                EstudoCapituloOrigem.estudo_capitulo_id == cap.id,
                EstudoCapituloOrigem.obra_capitulo_id == capitulo_obra.id,
            )
        ).first()
        if existe is None:
            session.add(EstudoCapituloOrigem(
                estudo_capitulo_id=cap.id,
                obra_capitulo_id=capitulo_obra.id,
                created_at=datetime.utcnow(),
            ))
            origens_novas += 1

    session.commit()
    return {
        "estudo_id": estudo.id,
        "obra": obra.titulo,
        "capitulos": len(selecionados),
        "novos": novos,
        "atualizados": atualizados,
        "origens_novas": origens_novas,
        "sem_origem": sem_origem,
        "sem_versao": sem_versao,
        "ignorados": [s.title for s in ignorados],
    }


def engine_de_teste():
    arquivo = Path(tempfile.gettempdir()) / f"estudo-aplicado-autoteste-{os.getpid()}.db"
    arquivo.unlink(missing_ok=True)
    return create_engine(f"sqlite:///{arquivo.as_posix()}"), arquivo


def engine_de_producao():
    from rxconfig import config

    return create_engine(config.db_url or "sqlite:///gsi_ebd.db")


# ── autoteste ──────────────────────────────────────────────────────────────

def _semear_obra(session: Session, titulo: str) -> None:
    obra = Obra(titulo=titulo, tipo="livro", created_at=datetime.utcnow())
    session.add(obra)
    session.flush()
    for ordem in range(1, 35):
        session.add(ObraCapitulo(
            obra_id=obra.id, ordem=ordem,
            titulo=f"Capitulo {ordem:02d} da obra", conteudo_md=f"obra {ordem}",
        ))
    session.commit()


def _semear_estudos(session: Session) -> None:
    for ordem in range(1, 35):
        study = Study(title=f"Cap. {ordem:02d} — Teste {ordem}", category="teste",
                      status="aprovado", created_at=datetime.utcnow())
        session.add(study)
        session.flush()
        session.add(StudyVersion(study_id=study.id, version=1,
                                 content_md=f"conteudo {ordem}", questions_json="[]",
                                 created_at=datetime.utcnow()))
    for i in range(1, 6):
        study = Study(title=f"Exemplo {i}", category="exemplo", status="aprovado",
                      created_at=datetime.utcnow())
        session.add(study)
        session.flush()
        session.add(StudyVersion(study_id=study.id, version=1,
                                 content_md=f"exemplo {i}", questions_json="[]",
                                 created_at=datetime.utcnow()))
    session.commit()


def autoteste() -> int:
    engine, arquivo = engine_de_teste()
    SQLModel.metadata.create_all(engine)
    falhas = 0

    def checar(condicao: bool, rotulo: str, detalhe: str = "") -> None:
        nonlocal falhas
        if condicao:
            print(f"OK    {rotulo} {detalhe}")
        else:
            print(f"FALHA {rotulo} {detalhe}")
            falhas += 1

    with Session(engine) as session:
        _semear_estudos(session)

        # F-11: sem a obra, aborta e nao cria nada
        try:
            gravar(session, "Estudo de Teste", "Obra de Teste")
            checar(False, "F-11 abortou sem a obra", "(nao levantou erro)")
        except PreCondicaoError:
            checar(True, "F-11 abortou sem a obra")
        checar(contar(session, Estudo) == 0 and contar(session, EstudoCapitulo) == 0,
               "F-11 nada foi criado",
               f"(estudos={contar(session, Estudo)}, capitulos={contar(session, EstudoCapitulo)})")

        _semear_obra(session, "Obra de Teste")

        resultado = gravar(session, "Estudo de Teste", "Obra de Teste")
        checar(resultado["capitulos"] == 34, "F-05 34 capitulos", f'(={resultado["capitulos"]})')
        checar(resultado["origens_novas"] == 34, "F-05 34 origens", f'(={resultado["origens_novas"]})')
        checar(len(resultado["ignorados"]) == 5, "N-06 5 exemplos ignorados",
               f'(={len(resultado["ignorados"])})')
        checar(contar(session, Estudo) == 1, "F-01 um estudo", f"(={contar(session, Estudo)})")

        fora_de_rascunho = session.exec(
            select(EstudoCapitulo).where(EstudoCapitulo.status != StudyStatus.RASCUNHO.value)
        ).all()
        checar(len(fora_de_rascunho) == 0, "F-06 tudo em rascunho", f"(fora={len(fora_de_rascunho)})")

        segunda = gravar(session, "Estudo de Teste", "Obra de Teste")
        checar(segunda["novos"] == 0 and segunda["origens_novas"] == 0,
               "RNF idempotente", f'(novos={segunda["novos"]}, origens={segunda["origens_novas"]})')
        checar(contar(session, EstudoCapitulo) == 34,
               "RNF nao duplicou", f"(capitulos={contar(session, EstudoCapitulo)})")

        conferido = conferir(session, "Obra de Teste")
        checar(conferido["selecionados"] == 34, "dry-run seleciona 34",
               f'(={conferido["selecionados"]})')

    engine.dispose()
    try:
        arquivo.unlink(missing_ok=True)
    except OSError as erro:
        print(f"(nao consegui apagar o SQLite de teste: {erro})")

    print(f"\nAUTOTESTE: {'PASS' if falhas == 0 else f'FAIL ({falhas})'}")
    return 0 if falhas == 0 else 1


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Importa o estudo aplicavel (capitulos + origem)")
    ap.add_argument("--obra", default=TITULO_OBRA_PADRAO)
    ap.add_argument("--titulo", default=TITULO_ESTUDO_PADRAO)
    ap.add_argument("--apply", action="store_true", help="grava (sem isso so confere)")
    ap.add_argument("--autoteste", action="store_true", help="SQLite descartavel")
    args = ap.parse_args()

    if args.autoteste:
        return autoteste()

    engine = engine_de_producao()
    print(f"banco: {engine.url.render_as_string(hide_password=True)}")
    try:
        with Session(engine) as session:
            plano = conferir(session, args.obra)
            print(f"obra: {plano['obra']} ({plano['capitulos_da_obra']} capitulos)")
            print(f"capitulos do livro encontrados: {plano['selecionados']}")
            if plano["ignorados"]:
                print(f"ignorados (sem 'Cap. NN'): {len(plano['ignorados'])}")
                for titulo in plano["ignorados"]:
                    print(f"  - {titulo}")
            if plano["sem_capitulo_de_obra"]:
                print(f"atencao: ordens sem capitulo na obra: {plano['sem_capitulo_de_obra']}")

            if not args.apply:
                print("\n(--apply nao foi passado: NADA foi gravado)")
                return 0

            resultado = gravar(session, args.titulo, args.obra)
            print(f"\nestudo: {args.titulo} (id {resultado['estudo_id']})")
            print(f"  capitulos:          {resultado['capitulos']}")
            print(f"  novos:              {resultado['novos']}")
            print(f"  atualizados:        {resultado['atualizados']}")
            print(f"  origens novas:      {resultado['origens_novas']}")
            print(f"  sem origem:         {resultado['sem_origem']}")
            print(f"  sem versao:         {resultado['sem_versao']}")
            print(f"  total capitulos:    {contar(session, EstudoCapitulo)}")
            print(f"  total origens:      {contar(session, EstudoCapituloOrigem)}")
    except PreCondicaoError as erro:
        print(f"\nABORTADO: {erro}")
        return 2
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
