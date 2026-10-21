"""Engine da v1. So abre o banco didasko_v1 e carimba o baseline.

O Alembic antigo (seis revisoes, target_metadata vazio) nao entra neste fluxo:
ele pode estar defasado e nao pode correr no banco da v0.
"""
from pathlib import Path

from fastapi import Request
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL
from sqlmodel import Session, SQLModel, create_engine

import gsi_ebd.models  # noqa: F401  (registra o metadata)

RAIZ = Path(__file__).resolve().parent
BASELINE = "0001_baseline"


def assert_banco_v1(url: str | URL) -> None:
    """Recusa qualquer banco que nao seja o didasko_v1.

    sqlite em memoria passa: e o banco dos testes, nao o da v0.
    """
    endereco = url if isinstance(url, URL) else make_url(url)
    if endereco.drivername.startswith("sqlite"):
        nome = endereco.database
        if nome in (None, "", ":memory:"):
            return
        if Path(nome).name != "didasko_v1.db":
            raise RuntimeError("sqlite da v1 tem de se chamar didasko_v1.db")
        return
    if endereco.database != "didasko_v1":
        raise RuntimeError("a v1 so abre o banco didasko_v1")


def criar_engine(url: str, **kwargs):
    assert_banco_v1(url)
    return create_engine(url, **kwargs)


def aplicar_baseline(engine) -> None:
    """Carimba o baseline. Nao executa as revisoes da v0."""
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext

    with engine.connect() as conexao:
        atual = MigrationContext.configure(conexao).get_current_revision()
        if atual == BASELINE:
            return
        if atual is not None:
            raise RuntimeError("o banco da v1 ja tem revisao que nao e o baseline")
        config = Config(str(RAIZ / "alembic.ini"))
        config.set_main_option("script_location", str(RAIZ / "alembic"))
        config.attributes["connection"] = conexao
        command.stamp(config, BASELINE)
        conexao.commit()


def iniciar_banco(engine) -> None:
    SQLModel.metadata.create_all(engine)
    aplicar_baseline(engine)


def sessao(request: Request):
    with Session(request.app.state.engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
