import bcrypt
import pytest
import re
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from gsi_ebd.models import Adendo, Obra, ObraCapitulo, Role, User, UserStatus
from gsi_ebd.services import flow, fontes
from v1.main import create_app

SENHA = "Senha-teste-123!"
NOVA = "Nova-senha-456!"


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    inventario = tmp_path / "inventario.csv"
    inventario.write_text("id;decisao\nF-001;entra\nF-002;depende\nF-003;nao_entra\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(inventario))
    fontes._carregar.cache_clear()
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
        admin = session.exec(select(User).where(User.role == int(Role.ADMIN))).one()
        obra = Obra(titulo="Obra de teste")
        versao = flow.importar(session, "F-001", obra, admin)
        session.add_all(
            [
                ObraCapitulo(obra_id=obra.id, ordem=1, titulo="Capitulo", conteudo_md="Texto inicial"),
                Adendo(obra_id=obra.id, codigo="ADO-01", titulo="Nota", texto="Nota inicial"),
            ]
        )
        session.commit()
        obra_id, versao_id = obra.id, versao.id
    with TestClient(app) as client:
        yield {
            "app": app,
            "client": client,
            "engine": engine,
            "obra_id": obra_id,
            "versao_id": versao_id,
            "inventario": inventario,
        }
    fontes._carregar.cache_clear()


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


def payload(sistema, token):
    with Session(sistema["engine"]) as session:
        esperado = flow.hash_obra(session, sistema["obra_id"])
    return {
        "csrf_token": token,
        "titulo": "Outra obra",
        "fonte_id": "F-001",
        "capitulo_ordem": "1",
        "capitulo_titulo": "Capitulo",
        "capitulo_texto": "Texto inicial",
        "adendo_codigo": "ADO-01",
        "adendo_titulo": "Nota",
        "adendo_texto": "Nota inicial",
        "versao_id": str(sistema["versao_id"]),
        "hash_esperado": esperado,
        "parecer": "Conferido",
        "ajustes": "Conferir nota",
        "ajustes_descritos": "Nota ajustada",
        "motivo": "Reavaliar",
        "posicao": "objeto",
        "texto": "Posicao registrada",
        "senha_atual": SENHA,
        "nova_senha": NOVA,
        "confirma_senha": NOVA,
    }
