import pytest
import secrets
from fastapi.testclient import TestClient
from jinja2 import StrictUndefined, UndefinedError
from sqlmodel import Session, select

from gsi_ebd.models import Ambiente, Role, User, UserStatus
from v1.auth import caminhos_da_app, destino
from v1.main import create_app
from v1.tests.conftest import SENHA, csrf, entrar


def test_rf01_destino_enxerga_rota_incluida_e_cai_na_raiz(sistema):
    caminhos = caminhos_da_app(sistema["app"])
    assert "/" in caminhos and "/login" in caminhos
    assert "/admin" not in caminhos

    class _pedido:
        app = sistema["app"]

    class _usuario:
        must_change_password = False
        role = int(Role.ADMIN)

    assert destino(_pedido(), _usuario()) == "/"


def test_rf01_login_logout_e_papel_vem_do_servidor(sistema):
    client = sistema["client"]
    assert client.get("/", follow_redirects=False).status_code == 401
    entrar(client, Role.ALUNO)
    pagina = client.get("/", headers={"X-Role": "1"})
    assert pagina.status_code == 200
    assert "Aluno" in pagina.text
    assert "Administrador" not in pagina.text
    token = csrf(pagina)
    saida = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert saida.status_code == 303 and saida.headers["location"] == "/login"
    assert client.get("/").status_code == 401


def test_rf01_cookie_httponly_secure_e_strictundefined(sistema):
    app = create_app(engine=sistema["engine"], secret_key=secrets.token_urlsafe(40), secure=True)
    with TestClient(app, base_url="https://testserver") as client:
        cookie = client.get("/login").headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "max-age=3600" in cookie
    assert sistema["app"].state.templates.env.undefined is StrictUndefined
    with pytest.raises(UndefinedError):
        sistema["app"].state.templates.env.from_string("{{ ausente }}").render()
    with pytest.raises(RuntimeError):
        create_app(engine=sistema["engine"], secret_key="curto")


def test_rf01_post_sem_csrf_e_token_de_outra_sessao(sistema):
    client = sistema["client"]
    assert client.post("/login", data={"email": "papel1@example.test", "senha": SENHA}).status_code == 403
    token = entrar(client, Role.ADMIN)
    with TestClient(sistema["app"]) as outro:
        assert outro.post("/login", data={"csrf_token": token}).status_code == 403
    antigo = csrf(client.get("/login"))
    assert client.post(
        "/logout",
        headers={"X-CSRF-Token": antigo},
        follow_redirects=False,
    ).status_code == 303
    assert client.post("/logout", data={"csrf_token": antigo}).status_code == 403


def test_rf01_senha_errada_suspenso_e_admin(sistema):
    client = sistema["client"]
    token = csrf(client.get("/login"))
    assert client.post(
        "/login",
        data={"csrf_token": token, "email": "papel1@example.test", "senha": "errada"},
    ).status_code == 401
    with Session(sistema["engine"]) as session:
        revisor = session.exec(select(User).where(User.role == int(Role.REVISOR))).one()
        revisor.status = UserStatus.SUSPENSO
        admin = session.exec(select(User).where(User.role == int(Role.ADMIN))).one()
        admin.status = UserStatus.SUSPENSO
        session.add(revisor)
        session.add(admin)
        session.commit()
    assert client.post(
        "/login",
        data={"csrf_token": token, "email": "papel5@example.test", "senha": SENHA},
    ).status_code == 401
    assert client.post(
        "/login",
        data={"csrf_token": token, "email": "papel1@example.test", "senha": SENHA},
        follow_redirects=False,
    ).status_code == 303


def test_rf01_ambiente_atual_na_raiz(sistema):
    client = sistema["client"]
    with Session(sistema["engine"]) as session:
        coordenador = session.exec(select(User).where(User.role == int(Role.COORDENADOR))).one()
        ambiente = Ambiente(nome="Igreja Centro", slug="igreja-centro", coordenador_id=coordenador.id)
        session.add(ambiente)
        session.commit()
        session.refresh(ambiente)
        coordenador.ambiente_id = ambiente.id
        session.add(coordenador)
        session.commit()
    entrar(client, Role.COORDENADOR)
    pagina = client.get("/")
    assert pagina.status_code == 200
    assert "Igreja Centro" in pagina.text
    client.post("/logout", data={"csrf_token": csrf(pagina)}, follow_redirects=False)
    entrar(client, Role.ALUNO)
    assert "Sem ambiente" in client.get("/").text
