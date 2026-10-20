import pytest
from fastapi.routing import APIRoute

from gsi_ebd.models import Role
from gsi_ebd.utils.rbac import PERMISSOES, pode
from v1.tests.conftest import NOVA, SENHA, csrf, entrar

# Chave None: rota publica, sem dependencia de papel.
ESPERADO = {
    ("GET", "/login"): None,
    ("POST", "/login"): None,
    ("GET", "/"): "rota:/",
    ("POST", "/logout"): "rota:/perfil/alterar-senha",
    ("GET", "/perfil/alterar-senha"): "rota:/perfil/alterar-senha",
    ("POST", "/perfil/alterar-senha"): "rota:/perfil/alterar-senha",
}


def _chaves(rota: APIRoute) -> list[str]:
    achadas = []

    def andar(dep):
        chave = getattr(getattr(dep, "call", None), "chave_permissao", None)
        if chave:
            achadas.append(chave)
        for filho in getattr(dep, "dependencies", ()) or ():
            andar(filho)

    andar(rota.dependant)
    return achadas


def _rotas(app) -> dict[tuple[str, str], APIRoute]:
    # FastAPI 0.150 guarda o router incluido; as rotas concretas ficam nele.
    pilha = list(app.routes)
    mapa = {}
    while pilha:
        rota = pilha.pop()
        original = getattr(rota, "original_router", None)
        if original is not None:
            pilha.extend(original.routes)
            continue
        if isinstance(rota, APIRoute):
            for metodo in rota.methods:
                if metodo in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    mapa[(metodo, rota.path)] = rota
    return mapa


def test_rf02_inventario_e_dependencia_da_matriz(sistema):
    mapa = _rotas(sistema["app"])
    assert set(mapa) == set(ESPERADO)
    for chave_rota, chave in ESPERADO.items():
        achadas = _chaves(mapa[chave_rota])
        if chave is None:
            assert achadas == []
        else:
            assert achadas == [chave]
            assert chave in PERMISSOES
    assert pode("rota:/admin", Role.ALUNO) is False
    assert pode("rota:/admin", Role.ADMIN) is True


@pytest.mark.parametrize("papel", list(Role))
@pytest.mark.parametrize("metodo,rota", [item for item in ESPERADO if item[0] == "GET"])
def test_rf02_render_por_papel(sistema, papel, metodo, rota):
    client = sistema["client"]
    chave = ESPERADO[(metodo, rota)]
    if chave is None:
        resposta = client.get(rota)
        assert resposta.status_code == 200
        assert "Didasko" in resposta.text
        return
    entrar(client, papel)
    resposta = client.request(metodo, rota, follow_redirects=False)
    if pode(chave, papel):
        assert resposta.status_code == 200, resposta.text
        assert "Didasko" in resposta.text
        assert f'data-rota="{rota}"' in resposta.text
    else:
        assert resposta.status_code == 403


def test_rf02_post_protegido_respeita_a_matriz(sistema):
    client = sistema["client"]
    token = entrar(client, Role.INSTRUTOR)
    saida = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert saida.status_code == 303
    token = entrar(client, Role.INSTRUTOR)
    troca = client.post(
        "/perfil/alterar-senha",
        data={
            "csrf_token": token,
            "senha_atual": SENHA,
            "nova_senha": NOVA,
            "confirma_senha": NOVA,
        },
        follow_redirects=False,
    )
    assert troca.status_code == 303 and troca.headers["location"] == "/"
