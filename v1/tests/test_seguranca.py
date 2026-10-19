import pytest
from fastapi.routing import APIRoute
from sqlmodel import Session, select
from gsi_ebd.models import Role, User
from gsi_ebd.utils.rbac import PERMISSOES
from v1.tests.conftest import csrf, entrar, payload, SENHA

ROTAS = [("POST", "/logout", "rota:/perfil/alterar-senha"), ("GET", "/perfil/alterar-senha", "rota:/perfil/alterar-senha"),
         ("POST", "/perfil/alterar-senha", "rota:/perfil/alterar-senha"), ("GET", "/admin/obras", "rota:/admin/obras"),
         ("GET", "/admin/obras/nova", "rota:/admin/obras"), ("POST", "/admin/obras", "rota:/admin/obras"),
         ("GET", "/admin/obras/{obra_id}", "rota:/admin/obras"),
         *[("POST", f"/admin/obras/{{obra_id}}/{a}", "rota:/admin/obras") for a in ("liberar", "alterar", "reenviar", "aceitar", "dispensar", "cancelar")],
         ("GET", "/revisor/obras", "rota:/revisor/obras"), ("GET", "/revisor/obras/{obra_id}", "rota:/revisor/obras"),
         *[("POST", f"/revisor/obras/{{obra_id}}/{a}", "rota:/revisor/obras") for a in ("revisar", "recusar", "solicitar", "posicionar")],
         ("GET", "/obras/{obra_id}", "rota:/obras")]
POSTS = [("POST", "/login", "publica"), *[r for r in ROTAS if r[0] == "POST"]]


def test_rf02_inventario_cobre_todas_as_rotas(sistema):
    reais = {(m.upper(), caminho) for caminho, operacoes in sistema["app"].openapi()["paths"].items()
             for m in operacoes if m in {"get", "post", "put", "patch", "delete"}}
    assert reais == {(m, p) for m, p, _ in ROTAS} | {("GET", "/login"), ("POST", "/login")}
    assert PERMISSOES["rota:/admin/obras"] == (Role.ADMIN,)
    assert PERMISSOES["rota:/revisor/obras"] == (Role.REVISOR,)
    assert PERMISSOES["rota:/obras"] == (Role.ADMIN, Role.REVISOR)


@pytest.mark.parametrize("papel", list(Role))
@pytest.mark.parametrize("metodo,rota,chave", ROTAS)
def test_rf02_matriz_rotas_servidor(sistema, papel, metodo, rota, chave):
    c = sistema["client"]
    token = entrar(c, papel)
    r = c.request(metodo, rota.format(obra_id=sistema["obra_id"]), data=payload(sistema, token) if metodo == "POST" else None, follow_redirects=False)
    assert r.status_code in ({200, 303, 409} if papel in PERMISSOES[chave] else {403}), r.text


@pytest.mark.parametrize("metodo,rota,chave", POSTS)
def test_rf03_todos_posts_rejeitam_sem_csrf(sistema, metodo, rota, chave):
    c = sistema["client"]
    entrar(c, PERMISSOES[chave][0] if chave != "publica" else Role.ADMIN)
    dados = payload(sistema, "")
    dados.pop("csrf_token")
    assert c.post(rota.format(obra_id=sistema["obra_id"]), data=dados, follow_redirects=False).status_code == 403


@pytest.mark.parametrize("metodo,rota,chave", ROTAS + [("GET", "/login", "rota:/login"), ("POST", "/login", "rota:/login")])
def test_h14_flag_bloqueia_todas_as_rotas_antes_da_troca(sistema, metodo, rota, chave):
    c = sistema["client"]
    papel = PERMISSOES[chave][0]
    token = entrar(c, papel)
    with Session(sistema["engine"]) as session:
        u = session.exec(select(User).where(User.role == papel)).one()
        u.must_change_password = True
        session.add(u)
        session.commit()
    r = c.request(metodo, rota.format(obra_id=sistema["obra_id"]), data=payload(sistema, token) if metodo == "POST" else None, follow_redirects=False)
    assert r.status_code in ({200, 303} if rota in {"/perfil/alterar-senha", "/logout"} else {403}), r.text


@pytest.mark.parametrize("papel", list(Role))
def test_h14_login_e_troca_real_desbloqueiam_papel(sistema, papel):
    c = sistema["client"]
    with Session(sistema["engine"]) as session:
        u = session.exec(select(User).where(User.role == papel)).one()
        u.must_change_password = True
        session.add(u)
        session.commit()
    r = c.post("/login", data={"csrf_token": csrf(c.get("/login")), "email": f"papel{int(papel)}@example.test", "senha": SENHA}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/perfil/alterar-senha"
    assert c.post("/perfil/alterar-senha", data=payload(sistema, csrf(c.get("/perfil/alterar-senha"))), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        import bcrypt
        u = session.exec(select(User).where(User.role == papel)).one()
        assert not u.must_change_password and bcrypt.checkpw(b"Nova-senha-456!", u.password_hash.encode())
    assert c.get("/perfil/alterar-senha").status_code == 200


def test_rf01_logout_revoga_cookie_e_nao_confia_em_papel_cliente(sistema):
    c = sistema["client"]
    token = entrar(c, Role.ALUNO)
    cookie = c.cookies.get("didasko_v1")
    assert c.get("/admin/obras", headers={"X-Role": "1"}).status_code == 403
    assert c.post("/logout", data={"csrf_token": token}, follow_redirects=False).status_code == 303
    c.cookies.clear()
    c.cookies.set("didasko_v1", cookie)
    assert c.get("/perfil/alterar-senha").status_code == 401


def test_rf03_token_de_outra_sessao_e_cookie_adulterado_nao_autorizam(sistema):
    from fastapi.testclient import TestClient
    c = sistema["client"]
    token = entrar(c, Role.ADMIN)
    with TestClient(sistema["app"]) as outro:
        assert outro.post("/login", data={"csrf_token": token}).status_code == 403
    c.cookies.clear()
    c.cookies.set("didasko_v1", "cookie-adulterado")
    assert c.get("/admin/obras").status_code == 401


def test_rf03_header_htmx_e_rotacao_do_token(sistema):
    c = sistema["client"]
    antigo = csrf(c.get("/login"))
    assert c.post("/login", headers={"X-CSRF-Token": antigo}, data={"email": "papel1@example.test", "senha": SENHA}, follow_redirects=False).status_code == 303
    assert c.post("/logout", data={"csrf_token": antigo}).status_code == 403
    novo = csrf(c.get("/perfil/alterar-senha"))
    assert c.post("/logout", headers={"X-CSRF-Token": novo}, follow_redirects=False).status_code == 303


def test_rf01_usuario_inativo_e_senha_errada_nao_entram(sistema):
    c = sistema["client"]
    token = csrf(c.get("/login"))
    assert c.post("/login", data={"csrf_token": token, "email": "papel1@example.test", "senha": "Errada"}).status_code == 401
    with Session(sistema["engine"]) as session:
        u = session.exec(select(User).where(User.role == Role.REVISOR)).one()
        u.status = "suspenso"
        session.add(u)
        session.commit()
    assert c.post("/login", data={"csrf_token": token, "email": "papel5@example.test", "senha": SENHA}).status_code == 401


def test_rf01_cookie_strictundefined_e_segredo_obrigatorio(sistema):
    import secrets
    from fastapi.testclient import TestClient
    from jinja2 import StrictUndefined, UndefinedError
    from v1.main import create_app
    app = create_app(engine=sistema["engine"], secret_key=secrets.token_urlsafe(40), secure=True)
    with TestClient(app, base_url="https://testserver") as c:
        cookie = c.get("/login").headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert sistema["app"].state.templates.env.undefined is StrictUndefined
    with pytest.raises(UndefinedError):
        sistema["app"].state.templates.env.from_string("{{ ausente }}").render()
    with pytest.raises(RuntimeError):
        create_app(engine=sistema["engine"], secret_key="curto")
