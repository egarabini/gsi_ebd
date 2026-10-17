"""Importa uma OBRA (a fonte) e seus capítulos para o banco.

A obra NÃO é o estudo: é o material de origem — um livro, uma coletânea ou um
condensado de vários livros. O estudo aplicável vem depois (ver
`Diagnostico/plano-bibliotecas.md`).

De onde lê: o texto em português da obra. No DOUTRINAS_CRISTAS ele está em
`docs/base/Capitulo_NN/`, e a convenção do projeto diz que a versão BOA é a
corrigida (`*_PT_v1.md`); a preservada (`*_PT.md`) é a reserva. O importador
prefere a primeira e cai para a segunda — quando a correção for feita, basta
rodar de novo.

Uso:
    python -m gsi_ebd.scripts.importar_obra                       # confere
    python -m gsi_ebd.scripts.importar_obra --apply                # grava
    python -m gsi_ebd.scripts.importar_obra --apply --autoteste    # SQLite descartável
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

from sqlalchemy import func, select  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from gsi_ebd.models import Doutrina, Obra, ObraCapitulo  # noqa: E402

# A corrigida primeiro, a preservada como reserva.
SUFIXOS = ("_PT_v1.md", "_PT.md")
RE_PASTA = re.compile(r"Capitulo_(\d{1,2})$", re.IGNORECASE)

# Sementes de orientacao. A tabela e cadastravel: isto e so o ponto de partida.
DOUTRINAS_INICIAIS = (
    "Batista", "Pentecostal", "Presbiteriano", "Adventista",
    "Metodista", "Não denominacional",
)


# ── funções puras (testáveis sem banco) ─────────────────────────────────────

def ordem_da_pasta(pasta: Path) -> int | None:
    """`Capitulo_07` -> 7."""
    achado = RE_PASTA.search(pasta.name)
    return int(achado.group(1)) if achado else None


def escolher_arquivo(pasta: Path) -> Path | None:
    """A versão corrigida (`_PT_v1`), se existir; senão a preservada (`_PT`)."""
    for sufixo in SUFIXOS:
        candidatos = sorted(p for p in pasta.glob(f"*{sufixo}") if p.is_file())
        if candidatos:
            return candidatos[0]
    return None


def ler_titulo(conteudo: str) -> str:
    """O primeiro título de nível 1 do markdown: `# Introdução à Teologia…`."""
    for linha in (conteudo or "").splitlines():
        texto = linha.strip()
        if texto.startswith("# "):
            return texto[2:].strip()
    return ""


def carregar_capitulos(base: Path) -> list[dict]:
    """Lê as pastas `Capitulo_NN` em ordem. Ignora o que não tem texto em PT."""
    capitulos: list[dict] = []
    for pasta in sorted(base.glob("Capitulo_*")):
        if not pasta.is_dir():
            continue
        ordem = ordem_da_pasta(pasta)
        arquivo = escolher_arquivo(pasta)
        if ordem is None or arquivo is None:
            continue
        conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
        capitulos.append({
            "ordem": ordem,
            "titulo": ler_titulo(conteudo) or arquivo.stem,
            "conteudo_md": conteudo,
            "arquivo": arquivo.name,
        })
    return sorted(capitulos, key=lambda c: c["ordem"])


# ── banco ──────────────────────────────────────────────────────────────────

def resolver_base(explicito: str | None) -> Path:
    if explicito:
        return Path(explicito)
    raiz = os.getenv("ESTUDOS_ROOT")
    if raiz:
        return Path(raiz) / "DOUTRINAS_CRISTAS" / "docs" / "base"
    return (Path(__file__).resolve().parents[3]
            / "DOUTRINAS_CRISTAS" / "docs" / "base")


def contar(session: Session, modelo) -> int:
    return int(session.execute(select(func.count()).select_from(modelo)).scalar_one())


def semear_doutrinas(session: Session) -> int:
    """Cria a lista inicial. Cadastrável: roda uma vez, não sobrescreve."""
    criadas = 0
    for nome in DOUTRINAS_INICIAIS:
        if session.exec(select(Doutrina).where(Doutrina.nome == nome)).first():
            continue
        session.add(Doutrina(nome=nome, created_at=datetime.utcnow()))
        criadas += 1
    session.commit()
    return criadas


def gravar(session: Session, titulo: str, capitulos: list[dict], origem: str) -> dict:
    """Idempotente por (título da obra, ordem do capítulo)."""
    obra = session.exec(select(Obra).where(Obra.titulo == titulo)).first()
    if obra is None:
        obra = Obra(titulo=titulo, tipo="livro", origem=origem,
                    created_at=datetime.utcnow())
        session.add(obra)
        session.flush()

    novos = atualizados = 0
    for cap in capitulos:
        existente = session.exec(
            select(ObraCapitulo).where(
                ObraCapitulo.obra_id == obra.id,
                ObraCapitulo.ordem == cap["ordem"],
            )
        ).first()
        if existente is None:
            session.add(ObraCapitulo(
                obra_id=obra.id,
                ordem=cap["ordem"],
                titulo=cap["titulo"],
                conteudo_md=cap["conteudo_md"],
                arquivo=cap["arquivo"],
            ))
            novos += 1
        else:
            mudou = (
                existente.titulo != cap["titulo"]
                or existente.conteudo_md != cap["conteudo_md"]
                or existente.arquivo != cap["arquivo"]
            )
            if mudou:
                existente.titulo = cap["titulo"]
                existente.conteudo_md = cap["conteudo_md"]
                existente.arquivo = cap["arquivo"]
                session.add(existente)
                atualizados += 1
    session.commit()
    return {"obra_id": obra.id, "novos": novos, "atualizados": atualizados}


def engine_de_teste():
    arquivo = Path(tempfile.gettempdir()) / f"obra-autoteste-{os.getpid()}.db"
    arquivo.unlink(missing_ok=True)
    return create_engine(f"sqlite:///{arquivo.as_posix()}"), arquivo


def engine_de_producao():
    from rxconfig import config

    return create_engine(config.db_url or "sqlite:///gsi_ebd.db")


def main() -> int:
    ap = argparse.ArgumentParser(description="Importa a obra (fonte) e seus capítulos")
    ap.add_argument("--base", default=None,
                    help="pasta com Capitulo_NN (padrão: DOUTRINAS_CRISTAS/docs/base)")
    ap.add_argument("--titulo", default="Doutrinas Cristãs", help="título da obra")
    ap.add_argument("--apply", action="store_true", help="grava (sem isso só confere)")
    ap.add_argument("--autoteste", action="store_true", help="SQLite descartável")
    args = ap.parse_args()

    base = resolver_base(args.base)
    print(f"base: {base}")
    if not base.is_dir():
        print(f"ERRO: não achei {base}")
        return 1

    capitulos = carregar_capitulos(base)
    print(f"capítulos encontrados: {len(capitulos)}")
    for cap in capitulos[:3]:
        print(f"  {cap['ordem']:02d} — {cap['titulo'][:58]}  ({cap['arquivo']})")
    if len(capitulos) > 3:
        print(f"  … e mais {len(capitulos) - 3}")
    total_kb = sum(len(c["conteudo_md"]) for c in capitulos) / 1024
    print(f"texto: {total_kb:,.0f} KB em markdown")

    if not args.apply:
        print("\n(--apply não foi passado: nada foi gravado)")
        return 0

    arquivo_sqlite = None
    if args.autoteste:
        engine, arquivo_sqlite = engine_de_teste()
        print(f"\nAUTOTESTE em {arquivo_sqlite}")
    else:
        engine = engine_de_producao()
        print(f"\nbanco: {engine.url.render_as_string(hide_password=True)}")

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        semeadas = semear_doutrinas(session)
        if semeadas:
            print(f"doutrinas criadas: {semeadas}")
        resultado = gravar(session, args.titulo, capitulos, origem=str(base))
        print(f"\nobra: {args.titulo} (id {resultado['obra_id']})")
        print(f"  capítulos novos:       {resultado['novos']}")
        print(f"  capítulos atualizados: {resultado['atualizados']}")
        print(f"  total no banco:        {contar(session, ObraCapitulo)}")
        print(f"  doutrinas no banco:    {contar(session, Doutrina)}")

    engine.dispose()
    if arquivo_sqlite:
        try:
            arquivo_sqlite.unlink(missing_ok=True)
        except OSError as erro:
            print(f"(não consegui apagar o SQLite de teste: {erro})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
