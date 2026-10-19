import os
from pathlib import Path
from sqlalchemy.engine import make_url
from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine
import gsi_ebd.models  # O create_all precisa do registro de todos os modelos.


def criar_engine(database_url=None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Configure DATABASE_URL para o banco exclusivo didasko_v1")
    parsed = make_url(url)
    if parsed.get_backend_name() == "postgresql":
        if parsed.database != "didasko_v1":
            raise RuntimeError("A v1 exige o banco didasko_v1")
    elif parsed.get_backend_name() == "sqlite":
        if parsed.database != ":memory:" and Path(parsed.database or "").name != "didasko_v1.db":
            raise RuntimeError("SQLite local deve usar didasko_v1.db")
    else:
        raise RuntimeError("Banco nao suportado")
    kwargs = {"connect_args": {"check_same_thread": False}} if parsed.get_backend_name() == "sqlite" else {}
    return create_engine(url, **kwargs)


def iniciar_banco(engine):
    SQLModel.metadata.create_all(engine)


def sessao(request: Request):
    with Session(request.app.state.engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
