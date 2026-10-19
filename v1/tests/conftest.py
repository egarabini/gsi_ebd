import re
import secrets
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool
from gsi_ebd.models import User, Role, Obra, ObraCapitulo, Adendo
from gsi_ebd.services import flow, fontes
from v1.main import create_app

SENHA = "Senha-teste-123!"
HASH = bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt(rounds=4)).decode()


def csrf(response):
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
    assert match, response.text[:500]
    return match.group(1)


def entrar(client, papel):
    token = csrf(client.get("/login"))
    response = client.post("/login", data={"csrf_token": token, "email": f"papel{int(papel)}@example.test", "senha": SENHA}, follow_redirects=False)
    assert response.status_code == 303, response.text
    return csrf(client.get("/perfil/alterar-senha"))


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    inventario = tmp_path / "inventario.csv"
    inventario.write_text("id;decisao\nF-001;entra\nF-002;depende\nF-003;nao_entra\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(inventario))
    fontes._carregar.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    app = create_app(engine=engine, secret_key=secrets.token_urlsafe(40), secure=False)
    with TestClient(app) as client:
        with Session(engine) as session:
            usuarios = [User(email=f"papel{int(p)}@example.test", role=p, status="ativo", must_change_password=False,
                             password_hash=HASH, nome_base=p.name) for p in Role]
            session.add_all(usuarios)
            session.flush()
            obra = Obra(titulo="Obra de teste")
            versao = flow.importar(session, "F-001", obra, next(u for u in usuarios if u.role == Role.ADMIN))
            session.add_all([ObraCapitulo(obra_id=obra.id, ordem=1, titulo="Capitulo", conteudo_md="Texto inicial"),
                             Adendo(obra_id=obra.id, codigo="ADO-01", titulo="Nota", texto="Nota inicial")])
            session.commit()
            obra_id, versao_id = obra.id, versao.id
        yield {"app": app, "engine": engine, "client": client, "obra_id": obra_id,
               "versao_id": versao_id, "inventario": inventario}
    engine.dispose()
    fontes._carregar.cache_clear()


def payload(sistema, token):
    with Session(sistema["engine"]) as session:
        esperado = flow.hash_obra(session, sistema["obra_id"])
    return {"csrf_token": token, "titulo": "Outra obra", "fonte_id": "F-001", "capitulo_ordem": "1",
            "capitulo_titulo": "Capitulo", "capitulo_texto": "Texto inicial", "adendo_codigo": "ADO-01",
            "adendo_titulo": "Nota", "adendo_texto": "Nota inicial", "versao_id": str(sistema["versao_id"]),
            "hash_esperado": esperado, "parecer": "Conferido", "ajustes": "Conferir nota", "ajustes_descritos": "Nota ajustada",
            "motivo": "Reavaliar", "posicao": "objeto", "texto": "Posicao registrada", "senha_atual": SENHA,
            "nova_senha": "Nova-senha-456!", "confirma_senha": "Nova-senha-456!"}
