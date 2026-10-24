"""Paineis so leitura, menu derivado e matriz das rotas /admin e /revisor."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from gsi_ebd.models import (
    Ambiente,
    AmbienteEstudo,
    Equipe,
    EquipeInstrutor,
    Estudo,
    Progress,
    Role,
    Study,
    StudyAssignment,
    StudyStatus,
    StudyVersion,
    Turma,
    TurmaMembro,
    User,
)
from gsi_ebd.utils import rbac
from v1.tests.conftest import entrar, payload

CHAVES = ("rota:/admin", "rota:/revisor")

PERMITIDOS = {
    "/admin": frozenset({Role.ADMIN}),
    "/revisor": frozenset({Role.REVISOR}),
}

NEGO_DE = {
    "/admin": Role.REVISOR,
    "/revisor": Role.ADMIN,
}

PERMITE_DE = {
    "/admin": Role.ADMIN,
    "/revisor": Role.REVISOR,
}

CELULAS = [
    (rota, papel, papel in permitidos)
    for rota, permitidos in PERMITIDOS.items()
    for papel in Role
]


def _hierarquia(sistema):
    with Session(sistema["engine"]) as session:
        coord = session.exec(select(User).where(User.role == int(Role.COORDENADOR))).one()
        inst = session.exec(select(User).where(User.role == int(Role.INSTRUTOR))).one()
        aluno = session.exec(select(User).where(User.role == int(Role.ALUNO))).one()
        inst.coordenador_id = coord.id
        aluno.instrutor_id = inst.id
        aluno.coordenador_id = coord.id
        ambiente = Ambiente(nome="Igreja de teste", slug="igreja-teste", coordenador_id=coord.id)
        session.add(ambiente)
        session.flush()
        catalogo = Study(title="Estudo escolhido", status=StudyStatus.APROVADO.value, is_active=True)
        session.add(catalogo)
        session.flush()
        versao_estudo = StudyVersion(study_id=catalogo.id, version=1, content_md="Texto")
        session.add(versao_estudo)
        session.flush()
        session.add(AmbienteEstudo(ambiente_id=ambiente.id, study_id=catalogo.id, escolhido_por=coord.id))
        equipe = Equipe(nome="Equipe basico", coordenador_id=coord.id, ambiente_id=ambiente.id)
        session.add(equipe)
        session.flush()
        session.add(EquipeInstrutor(equipe_id=equipe.id, instrutor_id=inst.id))
        turma = Turma(nome="Turma 1", instrutor_id=inst.id, coordenador_id=coord.id, ambiente_id=ambiente.id)
        session.add(turma)
        session.flush()
        session.add(TurmaMembro(turma_id=turma.id, user_id=aluno.id))
        session.add(
            Estudo(
                obra_id=sistema["obra_id"],
                titulo="Estudo dirigido da obra de teste",
                status=StudyStatus.APROVADO.value,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            StudyAssignment(
                user_id=aluno.id,
                study_id=catalogo.id,
                study_version_id=versao_estudo.id,
                assigned_by=coord.id,
                completed=False,
            )
        )
        session.add(
            Progress(
                user_id=aluno.id,
                study_id=catalogo.id,
                score=0.5,
                total_questions=2,
                correct_answers=1,
            )
        )
        session.commit()


def test_contrato_admin_e_revisor():
    assert rbac.PERMISSOES["rota:/admin"] == (Role.ADMIN,)
    assert rbac.PERMISSOES["rota:/revisor"] == (Role.REVISOR,)


def test_painel_admin_200_com_os_dados(sistema):
    _hierarquia(sistema)
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    pagina = client.get("/admin", follow_redirects=False)
    assert pagina.status_code == 200, pagina.text
    texto = pagina.text
    assert "Painel do administrador" in texto
    assert "Obra de teste" in texto
    assert "Estudo dirigido da obra de teste" in texto
    assert "Papel 2" in texto
    assert "Estudo escolhido" in texto
    assert "Papel 3" in texto
    assert "Papel 4" in texto
    assert "1/2" in texto


def test_painel_revisor_200_com_fila_e_historico(sistema):
    client = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(client, Role.REVISOR)
    pagina = client.get("/revisor", follow_redirects=False)
    assert pagina.status_code == 200, pagina.text
    assert "Painel do revisor" in pagina.text
    assert "Obra de teste" in pagina.text
    assert "Fila de revisão" in pagina.text
    client.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token), follow_redirects=False)
    client.post("/logout", data={"csrf_token": token})
    token = entrar(client, Role.ADMIN)
    client.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False)
    client.post("/logout", data={"csrf_token": token})
    entrar(client, Role.REVISOR)
    historico = client.get("/revisor", follow_redirects=False)
    assert historico.status_code == 200
    assert "vista" in historico.text
    assert "liberada" in historico.text


@pytest.mark.parametrize("rota,papel,permitido", CELULAS)
def test_matriz_paineis_celula_permitido_e_negado(sistema, rota, papel, permitido):
    client = sistema["client"]
    entrar(client, papel)
    status = client.get(rota, follow_redirects=False).status_code
    if permitido:
        assert status == 200, status
        assert "Didasko" in client.get(rota).text
        entrar(client, NEGO_DE[rota])
        assert client.get(rota, follow_redirects=False).status_code == 403
    else:
        assert status == 403, status
        entrar(client, PERMITE_DE[rota])
        permitido_status = client.get(rota, follow_redirects=False).status_code
        assert permitido_status == 200, permitido_status


def test_matriz_paineis_falha_sem_as_duas_chaves(sistema, monkeypatch):
    admin = sistema["client"]
    entrar(admin, Role.ADMIN)
    with TestClient(sistema["app"]) as revisor:
        entrar(revisor, Role.REVISOR)
        filtrado = {chave: valor for chave, valor in rbac.PERMISSOES.items() if chave not in CHAVES}
        monkeypatch.setattr(rbac, "PERMISSOES", filtrado)
        assert admin.get("/admin", follow_redirects=False).status_code == 403
        assert admin.get("/revisor", follow_redirects=False).status_code == 403
        assert revisor.get("/admin", follow_redirects=False).status_code == 403
        assert revisor.get("/revisor", follow_redirects=False).status_code == 403


def test_menu_admin_revisor_e_anonimo(sistema):
    client = sistema["client"]
    login = client.get("/login")
    assert login.status_code == 200
    assert 'aria-label="Principal"' not in login.text
    assert 'href="/admin"' not in login.text

    entrar(client, Role.ADMIN)
    admin = client.get("/admin").text
    assert 'href="/admin"' in admin
    assert 'href="/admin/obras"' in admin
    assert 'href="/admin#estudos"' in admin
    assert 'href="/admin#alunos"' in admin
    assert ">Sair<" in admin
    assert 'href="/revisor/obras"' not in admin

    entrar(client, Role.REVISOR)
    revisor = client.get("/revisor").text
    assert 'href="/revisor"' in revisor
    assert 'href="/revisor/obras"' in revisor
    assert ">Sair<" in revisor
    assert 'href="/admin/obras"' not in revisor
    assert 'href="/admin#estudos"' not in revisor
    assert 'href="/admin#alunos"' not in revisor
    assert 'href="/admin"' not in revisor


def test_menu_deriva_da_matriz(sistema, monkeypatch):
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    filtrado = {chave: valor for chave, valor in rbac.PERMISSOES.items() if chave != "rota:/admin"}
    monkeypatch.setattr(rbac, "PERMISSOES", filtrado)
    pagina = client.get("/admin/obras").text
    assert 'href="/admin/obras"' in pagina
    assert 'href="/admin#estudos"' not in pagina
    assert 'href="/admin#alunos"' not in pagina


def test_paineis_sao_so_leitura(sistema):
    client = sistema["client"]
    token = entrar(client, Role.ADMIN)
    admin = client.post("/admin", data={"csrf_token": token}, follow_redirects=False)
    assert admin.status_code in {403, 405}
    token = entrar(client, Role.REVISOR)
    revisor = client.post("/revisor", data={"csrf_token": token}, follow_redirects=False)
    assert revisor.status_code in {403, 405}
