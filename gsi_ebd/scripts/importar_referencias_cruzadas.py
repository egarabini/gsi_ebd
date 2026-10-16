"""Carrega as referências cruzadas do OpenBible no banco.

Dado de terceiros (CC-BY 4.0): ~344 mil pares "de → para" com votação da
comunidade. O arquivo é versionado em `DADOS_EXTERNOS/openbible/` e chega ao
container pelo volume `:ro` do conteúdo.

Uso:
    python -m gsi_ebd.scripts.importar_referencias_cruzadas             # confere, não grava
    python -m gsi_ebd.scripts.importar_referencias_cruzadas --apply     # grava
    python -m gsi_ebd.scripts.importar_referencias_cruzadas --apply --recarregar
    python -m gsi_ebd.scripts.importar_referencias_cruzadas --autoteste # SQLite descartável

Sem `--apply` nada é gravado — mesmo contrato do importador de estudos.

Onde o arquivo é procurado: `$ESTUDOS_ROOT/DADOS_EXTERNOS/openbible/cross_references.txt`
(no container `ESTUDOS_ROOT=/conteudo/ESTUDOS_BIBLICOS`), ou o que vier em
`--arquivo`.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import delete, func, insert, select  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from gsi_ebd.models import ReferenciaCruzada  # noqa: E402
from gsi_ebd.utils.livros import por_osis  # noqa: E402


def resolver_arquivo(explicito: str | None) -> Path:
    """Descobre o TSV: `--arquivo`, ou `$ESTUDOS_ROOT/DADOS_EXTERNOS/openbible/`."""
    if explicito:
        return Path(explicito)
    raiz = os.getenv("ESTUDOS_ROOT")
    if raiz:
        return Path(raiz) / "DADOS_EXTERNOS" / "openbible" / "cross_references.txt"
    # Sem ESTUDOS_ROOT: layout do repositório, para rodar localmente.
    # parents: [0]=scripts [1]=gsi_ebd [2]=GSI_EBD [3]=ESTUDOS_BIBLICOS
    return (
        Path(__file__).resolve().parents[3]
        / "DADOS_EXTERNOS"
        / "openbible"
        / "cross_references.txt"
    )


def ler_tsv(caminho: Path):
    """Gera (de, para, votos) do arquivo. A primeira linha é o cabeçalho CC-BY."""
    with caminho.open(encoding="utf-8") as fh:
        cabecalho = fh.readline().strip()
        for linha in fh:
            partes = linha.rstrip("\n").split("\t")
            if len(partes) < 3:
                continue
            de, para, votos = partes[0], partes[1], partes[2]
            try:
                votos_int = int(votos)
            except ValueError:
                continue
            if not de or not para:
                continue
            yield de, para, votos_int, cabecalho


def conferir(caminho: Path) -> dict:
    """Lê o arquivo inteiro e devolve as estatísticas — sem tocar no banco."""
    total = 0
    com_intervalo = 0
    negativos = 0
    codigos: set = set()
    cabecalho = ""
    for de, para, votos, cabecalho in ler_tsv(caminho):
        total += 1
        if "-" in para:
            com_intervalo += 1
        if votos < 0:
            negativos += 1
        codigos.add(de.split(".", 1)[0])
    return {
        "total": total,
        "com_intervalo": com_intervalo,
        "negativos": negativos,
        "cabecalho": cabecalho,
        "codigos": codigos,
    }


def carregar(session: Session, caminho: Path, lote: int = 5000) -> int:
    """Trunca e insere tudo. Devolve quantas linhas entraram."""
    session.execute(delete(ReferenciaCruzada))
    session.commit()

    inseridos = 0
    buffer: list[dict] = []
    for de, para, votos, _ in ler_tsv(caminho):
        buffer.append({"de_versiculo": de, "para_versiculo": para, "votos": votos})
        if len(buffer) >= lote:
            session.execute(insert(ReferenciaCruzada), buffer)
            inseridos += len(buffer)
            buffer.clear()
    if buffer:
        session.execute(insert(ReferenciaCruzada), buffer)
        inseridos += len(buffer)
    session.commit()
    return inseridos


def contar(session: Session, votos_minimos: int | None = None) -> int:
    """Conta linhas da tabela.

    Usa `session.execute(...).scalar_one()` de propósito: via `session.exec()` o
    resultado de `func.count()` volta como `Row`, e formatar isso estoura em
    tempo de execução.
    """
    consulta = select(func.count()).select_from(ReferenciaCruzada)
    if votos_minimos is not None:
        consulta = consulta.where(ReferenciaCruzada.votos >= votos_minimos)
    return int(session.execute(consulta).scalar_one())


def engine_de_teste():
    """SQLite descartável — para conferir o caminho de escrita sem risco.

    Usa um arquivo no diretório temporário do sistema em vez de `mkdtemp()`: o
    diretório criado pelo Python é mais um para limpar, e neste ambiente de
    desenvolvimento o SQLite não consegue abrir arquivo dentro dele.
    """
    arquivo = Path(tempfile.gettempdir()) / f"crossref-autoteste-{os.getpid()}.db"
    arquivo.unlink(missing_ok=True)
    return create_engine(f"sqlite:///{arquivo.as_posix()}"), arquivo


def engine_de_producao():
    from rxconfig import config

    return create_engine(config.db_url or "sqlite:///gsi_ebd.db")


def main() -> int:
    parser = argparse.ArgumentParser(description="Carrega as referências cruzadas do OpenBible")
    parser.add_argument("--arquivo", default=None, help="caminho do cross_references.txt")
    parser.add_argument("--apply", action="store_true", help="grava no banco (sem isso, só confere)")
    parser.add_argument(
        "--recarregar",
        action="store_true",
        help="apaga o que existe e recarrega (o dado é um retrato periódico)",
    )
    parser.add_argument("--autoteste", action="store_true", help="roda num SQLite descartável")
    args = parser.parse_args()

    caminho = resolver_arquivo(args.arquivo)
    print(f"arquivo: {caminho}")
    if not caminho.exists():
        print(f"ERRO: não encontrei {caminho}")
        print("       (no container o volume do conteúdo fica em ESTUDOS_ROOT)")
        return 1

    inicio = time.time()
    info = conferir(caminho)
    print(f"cabeçalho: {info['cabecalho']}")
    print(f"pares lidos: {info['total']:,}")
    print(f"  com intervalo no destino: {info['com_intervalo']:,}")
    print(f"  com votos negativos:      {info['negativos']:,}")

    desconhecidos = sorted(c for c in info["codigos"] if por_osis(c) is None)
    if desconhecidos:
        print(f"AVISO: códigos de livro fora do mapa canônico: {desconhecidos}")
    else:
        print(f"livros: {len(info['codigos'])} — todos no mapa canônico")

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
        existentes = contar(session)
        if existentes and not args.recarregar:
            print(
                f"a tabela já tem {existentes:,} linhas — nada a fazer.\n"
                "Use --recarregar para substituir pelo retrato do arquivo."
            )
            return 0
        if existentes:
            print(f"apagando {existentes:,} linhas antigas (--recarregar)")

        inseridos = carregar(session, caminho)
        gravados = contar(session)
        forte = contar(session, votos_minimos=10)

    print(f"\ninseridos: {inseridos:,}")
    print(f"no banco:  {gravados:,}")
    print(f"  com votos >= 10 (o que a curadoria usa): {forte:,}")
    print(f"tempo: {time.time() - inicio:.1f}s")

    engine.dispose()  # sem isso o arquivo do SQLite fica preso e o unlink falha no Windows
    if arquivo_sqlite:
        try:
            arquivo_sqlite.unlink(missing_ok=True)
        except OSError as erro:
            print(f"(não consegui apagar o SQLite de teste: {erro})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
