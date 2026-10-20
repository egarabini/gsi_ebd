import bcrypt
import pytest
import re
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from gsi_ebd.models import Role, User, UserStatus
from v1.main import create_app

SENHA = "Senha-teste-123!"
NOVA = "Nova-senha-456!"


@pytest.fixture
def sistema():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app = create_app(engine=engine, secret_key="k" * 40, secure=False)
    with Session(engine) as session:
        for papel in Role:
            session.add(
                User(
                    email=f"papel{int(papel)}@example.test",
                    nome_base=f"Papel {int(papel)}",
                    nome_completo=f"Papel {int(papel)}",
                    password_hash=bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt(rounds=4)).decode(),
                    status=UserStatus.ATIVO,
                    role=int(papel),
                    must_change_password=False,
                )
            )
        session.commit()
    with TestClient(app) as client:
        yield {"app": app, "client": client, "engine": engine}


def csrf(resposta) -> str:
    achado = re.search(r'name="csrf_token" value="([^"]+)"', resposta.text)
    assert achado, resposta.text
    return achado.group(1)


def entrar(client, papel) -> str:
    token = csrf(client.get("/login"))
    resposta = client.post(
        "/login",
        data={"csrf_token": token, "email": f"papel{int(papel)}@example.test", "senha": SENHA},
        follow_redirects=False,
    )
    assert resposta.status_code == 303, resposta.text
    return csrf(client.get(resposta.headers["location"]))
