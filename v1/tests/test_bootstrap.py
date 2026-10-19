import pytest
from sqlmodel import Session, select
from gsi_ebd.models import User, Role
from v1.db import criar_engine
from v1.criar_usuario import criar_usuario


def test_rf01_bootstrap_exige_troca_e_nao_redefine_conta(sistema):
    with Session(sistema["engine"]) as session:
        uid = criar_usuario(session, "novo@example.test", Role.ADMIN, "Senha-temporaria-123")
        user = session.get(User, uid)
        assert user.must_change_password and user.status == "ativo"
        with pytest.raises(ValueError, match="ja existe"):
            criar_usuario(session, user.email, Role.ADMIN, "Outra-senha-123")


@pytest.mark.parametrize("url", ["postgresql://localhost/legado", "sqlite:///legado.db"])
def test_rf01_v1_nao_aceita_banco_legado(url):
    with pytest.raises(RuntimeError):
        criar_engine(url)
