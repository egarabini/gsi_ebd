"""Matriz de papéis das obras: 15 celulas, cada uma com permitido E negado.

A prova da vacuidade remove as 3 chaves e confirma que o permitido passa a 403
(a matriz falharia). Lição do marco 1: so o permitido passa com o rbac vazio
se a guarda nao consulta a matriz.
"""
import pytest

from gsi_ebd.models import Role
from gsi_ebd.utils import rbac
from v1.tests.conftest import entrar, payload

CHAVES = ("rota:/admin/obras", "rota:/revisor/obras", "rota:/obras")

PERMITIDOS = {
    "/admin/obras": frozenset({Role.ADMIN}),
    "/revisor/obras": frozenset({Role.REVISOR}),
    "/obras": frozenset({Role.ADMIN, Role.REVISOR}),
}

NEGO_DE = {
    "/admin/obras": Role.REVISOR,
    "/revisor/obras": Role.ADMIN,
    "/obras": Role.ALUNO,
}

PERMITE_DE = {
    "/admin/obras": Role.ADMIN,
    "/revisor/obras": Role.REVISOR,
    "/obras": Role.ADMIN,
}

CELULAS = [
    (rota, papel, papel in permitidos)
    for rota, permitidos in PERMITIDOS.items()
    for papel in Role
]


def test_contrato_das_tres_chaves():
    assert rbac.PERMISSOES["rota:/admin/obras"] == (Role.ADMIN,)
    assert rbac.PERMISSOES["rota:/revisor/obras"] == (Role.REVISOR,)
    assert rbac.PERMISSOES["rota:/obras"] == (Role.ADMIN, Role.REVISOR)


@pytest.mark.parametrize("rota,papel,permitido", CELULAS)
def test_matriz_obras_celula_permitido_e_negado(sistema, rota, papel, permitido):
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


def test_post_obras_sem_csrf_e_403(sistema):
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    dados = payload(sistema, "")
    dados.pop("csrf_token")
    assert client.post("/admin/obras", data=dados, follow_redirects=False).status_code == 403
    entrar(client, Role.REVISOR)
    dados = payload(sistema, "")
    dados.pop("csrf_token")
    assert client.post(
        f"/revisor/obras/{sistema['obra_id']}/revisar",
        data=dados,
        follow_redirects=False,
    ).status_code == 403


def test_matriz_obras_falha_sem_as_tres_chaves(sistema, monkeypatch):
    filtrado = {chave: valor for chave, valor in rbac.PERMISSOES.items() if chave not in CHAVES}
    monkeypatch.setattr(rbac, "PERMISSOES", filtrado)
    client = sistema["client"]
    entrar(client, Role.ADMIN)
    assert client.get("/admin/obras", follow_redirects=False).status_code == 403
    assert client.get("/obras", follow_redirects=False).status_code == 403
    entrar(client, Role.REVISOR)
    assert client.get("/revisor/obras", follow_redirects=False).status_code == 403
    assert client.get("/obras", follow_redirects=False).status_code == 403
