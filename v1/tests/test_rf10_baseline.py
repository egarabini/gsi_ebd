import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlmodel import Session, select

from gsi_ebd.models import User
from v1.db import BASELINE, RAIZ, assert_banco_v1


def test_rf10_recusa_banco_que_nao_e_didasko_v1():
    assert_banco_v1("sqlite://")
    assert_banco_v1("sqlite:///./didasko_v1.db")
    with pytest.raises(RuntimeError):
        assert_banco_v1("sqlite:///./gsi_ebd.db")
    with pytest.raises(RuntimeError):
        assert_banco_v1("postgresql+psycopg2://didasko:segredo@postgres:5432/didasko")
    with pytest.raises(RuntimeError):
        assert_banco_v1("postgresql+psycopg2://didasko:segredo@didasko_postgres:5432/didasko")


def test_rf10_baseline_carimbado_e_so_ele(sistema):
    engine = sistema["engine"]
    with engine.connect() as conexao:
        revisao = conexao.exec_driver_sql("select version_num from alembic_version").scalar()
    assert revisao == BASELINE
    tabelas = set(inspect(engine).get_table_names())
    assert "user" in tabelas
    assert "alembic_version" in tabelas
    config = Config()
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    assert ScriptDirectory.from_config(config).get_heads() == [BASELINE]
    with Session(engine) as session:
        assert session.exec(select(User)).all()
