"""Criacao do Estudo, avaliacoes ADR-020, matriz e fake no painel (DEM-017 fatia 2)."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from gsi_ebd.models import (
    Estudo,
    EstudoCapitulo,
    EstudoVersao,
    EstudoVersaoCapitulo,
    Progress,
    QuestionType,
    Role,
    Study,
    StudyAssignment,
    StudyStatus,
    StudyVersion,
    User,
    UserResponse,
    UserStatus,
)
from gsi_ebd.services import flow_estudo
from gsi_ebd.utils import rbac
from v1.seed_homolog_estudo import ALUNOS_FAKE
from v1.tests.conftest import entrar

CHAVES = ("rota:/admin/estudos", "rota:/admin/estudos/nova", "rota:/revisor/avaliacoes")

PERMITIDOS = {
    "/admin/estudos": frozenset({Role.ADMIN}),
    "/admin/estudos/nova": frozenset({Role.ADMIN}),
    "/revisor/avaliacoes": frozenset({Role.REVISOR}),
}

CELULAS = [
    (rota, papel, papel in permitidos)
    for rota, permitidos in PERMITIDOS.items()
    for papel in Role
]


def dados_estudo(sistema, token, **extra):
    base = {
        "csrf_token": token,
        "obra_id": str(sistema["obra_id"]),
        "titulo": "Estudo dirigido de teste",
        "descricao": "Obra aplicada em capitulos",
        "capitulo_ordem": "1",
        "capitulo_titulo": "Capitulo 1",
        "capitulo_texto": "Texto do estudo.",
        "capitulo_questoes": "[]",
        "parecer": "Conferido",
        "ajustes": "Ajuste pontual",
        "ajustes_descritos": "Ajuste aplicado",
    }
    base.update(extra)
    return base


def criar_estudo(sistema, token=None):
    client = sistema["client"]
    if token is None:
        token = entrar(client, Role.ADMIN)
    resposta = client.post(
        "/admin/estudos/nova",
        data=dados_estudo(sistema, token),
        follow_redirects=False,
    )
    assert resposta.status_code == 303, resposta.text
    estudo_id = int(resposta.headers["location"].rstrip("/").rsplit("/", 1)[-1])
    return estudo_id, token


def test_criar_estudo_post_303_e_grava(sistema):
    estudo_id, _token = criar_estudo(sistema)
    with Session(sistema["engine"]) as session:
        estudo = session.get(Estudo, estudo_id)
        assert estudo is not None
        assert estudo.titulo == "Estudo dirigido de teste"
        assert estudo.status == "em_revisao"
        caps = session.exec(select(EstudoCapitulo).where(EstudoCapitulo.estudo_id == estudo_id)).all()
        assert len(caps) == 1
        assert caps[0].titulo == "Capitulo 1"
        versao = session.exec(select(EstudoVersao).where(EstudoVersao.estudo_id == estudo_id)).one()
        assert versao.numero == 1 and versao.status == "em_revisao"


def test_lista_estudos_200_com_os_criados(sistema):
    criar_estudo(sistema)
    client = sistema["client"]
    pagina = client.get("/admin/estudos", follow_redirects=False)
    assert pagina.status_code == 200, pagina.text
    assert "Estudo dirigido de teste" in pagina.text
    assert "em_revisao" in pagina.text


def test_fila_revisor_200_com_o_estudo_em_revisao(sistema):
    _estudo_id, token = criar_estudo(sistema)
    client = sistema["client"]
    client.post("/logout", data={"csrf_token": token})
    entrar(client, Role.REVISOR)
    pagina = client.get("/revisor/avaliacoes", follow_redirects=False)
    assert pagina.status_code == 200, pagina.text
    assert "Estudo dirigido de teste" in pagina.text
    assert "Fila de revisão" in pagina.text or "Fila de revisao" in pagina.text


def test_parecer_revisor_303_admin_403(sistema):
    estudo_id, token = criar_estudo(sistema)
    client = sistema["client"]
    admin_parecer = client.post(
        f"/revisor/avaliacoes/{estudo_id}/revisar",
        data=dados_estudo(sistema, token),
        follow_redirects=False,
    )
    assert admin_parecer.status_code == 403
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.REVISOR)
    with Session(sistema["engine"]) as session:
        esperado = flow_estudo.hash_estudo(session, estudo_id)
        versao = session.exec(select(EstudoVersao).where(EstudoVersao.estudo_id == estudo_id)).one()
        versao_id = versao.id
    dados = dados_estudo(sistema, token, hash_esperado=esperado, versao_id=str(versao_id))
    parecer = client.post(
        f"/revisor/avaliacoes/{estudo_id}/revisar",
        data=dados,
        follow_redirects=False,
    )
    assert parecer.status_code == 303, parecer.text
    with Session(sistema["engine"]) as session:
        versao = session.get(EstudoVersao, versao_id)
        assert versao.status == "aguardando_admin"
        assert versao.revisor_id is not None


def test_liberacao_exige_os_dois_admin_sozinho_409(sistema):
    estudo_id, token = criar_estudo(sistema)
    client = sistema["client"]
    with Session(sistema["engine"]) as session:
        versao = session.exec(select(EstudoVersao).where(EstudoVersao.estudo_id == estudo_id)).one()
        versao_id = versao.id
    sozinho = client.post(
        f"/admin/estudos/{estudo_id}/liberar",
        data=dados_estudo(sistema, token, versao_id=str(versao_id)),
        follow_redirects=False,
    )
    assert sozinho.status_code == 409, sozinho.text
    with Session(sistema["engine"]) as session:
        assert session.get(EstudoVersao, versao_id).status == "em_revisao"
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.REVISOR)
    with Session(sistema["engine"]) as session:
        esperado = flow_estudo.hash_estudo(session, estudo_id)
    assert client.post(
        f"/revisor/avaliacoes/{estudo_id}/revisar",
        data=dados_estudo(sistema, token, hash_esperado=esperado, versao_id=str(versao_id)),
        follow_redirects=False,
    ).status_code == 303
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.ADMIN)
    assert client.post(
        f"/admin/estudos/{estudo_id}/liberar",
        data=dados_estudo(sistema, token, versao_id=str(versao_id)),
        follow_redirects=False,
    ).status_code == 303
    with Session(sistema["engine"]) as session:
        estudo = session.get(Estudo, estudo_id)
        versao = session.get(EstudoVersao, versao_id)
        assert estudo.status == "liberada"
        assert versao.status == "liberada"
        assert versao.hash_visto and versao.hash_liberado


def test_n_imutavel_ciclo_cria_n_mais_1(sistema):
    estudo_id, token = criar_estudo(sistema)
    client = sistema["client"]
    with Session(sistema["engine"]) as session:
        versao = session.exec(select(EstudoVersao).where(EstudoVersao.estudo_id == estudo_id)).one()
        versao_id = versao.id
        esperado = flow_estudo.hash_estudo(session, estudo_id)
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.REVISOR)
    client.post(
        f"/revisor/avaliacoes/{estudo_id}/revisar",
        data=dados_estudo(sistema, token, hash_esperado=esperado, versao_id=str(versao_id)),
    )
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.ADMIN)
    congelado = dados_estudo(sistema, token, versao_id=str(versao_id), capitulo_texto="Texto congelado")
    assert client.post(
        f"/admin/estudos/{estudo_id}/liberar",
        data=congelado,
        follow_redirects=False,
    ).status_code == 303
    n1 = dados_estudo(sistema, token, versao_id=str(versao_id), capitulo_texto="Texto da N+1")
    assert client.post(
        f"/admin/estudos/{estudo_id}/alterar",
        data=n1,
        follow_redirects=False,
    ).status_code == 303
    with Session(sistema["engine"]) as session:
        n = session.get(EstudoVersao, versao_id)
        nova = session.exec(
            select(EstudoVersao).where(EstudoVersao.estudo_id == estudo_id, EstudoVersao.numero == 2)
        ).one()
        snapshot = session.exec(
            select(EstudoVersaoCapitulo).where(
                EstudoVersaoCapitulo.versao_id == n.id,
                EstudoVersaoCapitulo.momento == "liberado",
            )
        ).one()
        assert snapshot.conteudo_md == "Texto congelado"
        assert n.status == "liberada"
        assert nova.numero == 2 and nova.status == "em_revisao"


@pytest.mark.parametrize(
    "texto,equivalente",
    [("A\nB\nC", "A\r\nB\rC"), ("Caf\u00e9", "Cafe\u0301")],
)
def test_hash_estudo_lf_nfc(texto, equivalente):
    cap_a = EstudoCapitulo(estudo_id=1, ordem=1, titulo="Titulo", conteudo_md=texto)
    cap_b = EstudoCapitulo(estudo_id=1, ordem=1, titulo="Titulo", conteudo_md=equivalente)
    assert flow_estudo.hash_estudo_capitulo(cap_a) == flow_estudo.hash_estudo_capitulo(cap_b)


def test_fake_na_lista_do_painel(sistema):
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    with Session(sistema["engine"]) as session:
        modelo = session.exec(select(User).where(User.email == "papel4@example.test")).one()
        catalogo = Study(title="Estudo fake", status=StudyStatus.APROVADO.value, is_active=True)
        session.add(catalogo)
        session.flush()
        versao = StudyVersion(study_id=catalogo.id, version=1, content_md="Texto", questions_json="[]")
        session.add(versao)
        session.flush()
        for dados in ALUNOS_FAKE:
            aluno = User(
                email=dados["email"],
                nome_base=dados["nome_base"],
                nome_completo=dados["nome_completo"],
                password_hash=modelo.password_hash,
                status=UserStatus.ATIVO,
                role=int(Role.ALUNO),
                must_change_password=False,
            )
            session.add(aluno)
            session.flush()
            session.add(
                StudyAssignment(
                    user_id=aluno.id,
                    study_id=catalogo.id,
                    study_version_id=versao.id,
                    assigned_by=0,
                    completed=True,
                )
            )
            session.add(
                Progress(
                    user_id=aluno.id,
                    study_id=catalogo.id,
                    score=1.0,
                    total_questions=1,
                    correct_answers=1,
                )
            )
            session.add(
                UserResponse(
                    user_id=aluno.id,
                    study_version_id=versao.id,
                    question_key="q1",
                    question_type=int(QuestionType.TRUE_FALSE),
                    answer="sim",
                    is_correct=True,
                    created_at=datetime.now(timezone.utc),
                )
            )
        session.commit()
    pagina = client.get("/admin", follow_redirects=False)
    assert pagina.status_code == 200, pagina.text
    assert "Aluno Fake A" in pagina.text
    assert "Aluno Fake B" in pagina.text
    assert "1/1" in pagina.text
    assert "q1" in pagina.text


@pytest.mark.parametrize("rota,papel,permitido", CELULAS)
def test_matriz_estudos_permitido_e_negado(sistema, rota, papel, permitido):
    client = sistema["client"]
    entrar(client, papel)
    status = client.get(rota, follow_redirects=False).status_code
    if permitido:
        assert status == 200, status
    else:
        assert status == 403, status


def test_matriz_estudos_falha_sem_as_chaves(sistema, monkeypatch):
    admin = sistema["client"]
    entrar(admin, Role.ADMIN)
    with TestClient(sistema["app"]) as revisor:
        entrar(revisor, Role.REVISOR)
        filtrado = {chave: valor for chave, valor in rbac.PERMISSOES.items() if chave not in CHAVES}
        monkeypatch.setattr(rbac, "PERMISSOES", filtrado)
        for rota in PERMITIDOS:
            assert admin.get(rota, follow_redirects=False).status_code == 403
            assert revisor.get(rota, follow_redirects=False).status_code == 403


def test_menu_estudos_e_avaliacoes(sistema):
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    admin = client.get("/admin").text
    assert 'href="/admin/estudos"' in admin
    assert ">Estudos<" in admin
    assert 'href="/revisor/avaliacoes"' not in admin
    entrar(client, Role.REVISOR)
    revisor = client.get("/revisor").text
    assert 'href="/revisor/avaliacoes"' in revisor
    assert "Avalia" in revisor
    assert 'href="/admin/estudos"' not in revisor
