import bcrypt
import pytest
from sqlmodel import Session, select

from gsi_ebd.models import Role, User
from v1.tests.conftest import NOVA, SENHA, csrf, entrar

BLOQUEADAS = ("/", "/login")
LIBERADAS = ("/perfil/alterar-senha", "/logout")


@pytest.mark.parametrize("papel", list(Role))
def test_rf06_h14_flag_so_deixa_troca_e_logout(sistema, papel):
    client = sistema["client"]
    token = entrar(client, papel)
    with Session(sistema["engine"]) as session:
        usuario = session.exec(select(User).where(User.role == int(papel))).one()
        usuario.must_change_password = True
        session.add(usuario)
        session.commit()
    for rota in BLOQUEADAS:
        assert client.get(rota, follow_redirects=False).status_code == 403
    assert client.post("/login", data={"csrf_token": token, "email": "x", "senha": "y"}).status_code == 403
    pagina = client.get("/perfil/alterar-senha")
    assert pagina.status_code == 200
    assert client.post("/logout", data={"csrf_token": csrf(pagina)}, follow_redirects=False).status_code == 303


@pytest.mark.parametrize("papel", list(Role))
def test_rf06_h14_troca_real_desbloqueia(sistema, papel):
    client = sistema["client"]
    with Session(sistema["engine"]) as session:
        usuario = session.exec(select(User).where(User.role == int(papel))).one()
        usuario.must_change_password = True
        session.add(usuario)
        session.commit()
    token = csrf(client.get("/login"))
    entrada = client.post(
        "/login",
        data={"csrf_token": token, "email": f"papel{int(papel)}@example.test", "senha": SENHA},
        follow_redirects=False,
    )
    assert entrada.status_code == 303 and entrada.headers["location"] == "/perfil/alterar-senha"
    troca = client.post(
        "/perfil/alterar-senha",
        data={
            "csrf_token": csrf(client.get("/perfil/alterar-senha")),
            "senha_atual": SENHA,
            "nova_senha": NOVA,
            "confirma_senha": NOVA,
        },
        follow_redirects=False,
    )
    assert troca.status_code == 303 and troca.headers["location"] == "/"
    with Session(sistema["engine"]) as session:
        usuario = session.exec(select(User).where(User.role == int(papel))).one()
        assert usuario.must_change_password is False
        assert bcrypt.checkpw(NOVA.encode(), usuario.password_hash.encode())
        assert usuario.status == "ativo"
    assert client.get("/").status_code == 200
    assert "Didasko" in client.get("/").text
