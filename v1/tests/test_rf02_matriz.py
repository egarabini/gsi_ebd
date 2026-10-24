import pytest
from fastapi import Depends
from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRoute

from gsi_ebd.models import Role, User
from gsi_ebd.utils.rbac import PERMISSOES
from v1.auth import exigir
from v1.tests.conftest import NOVA, SENHA, csrf, entrar

# Chave None: rota publica, sem dependencia de papel.
ESPERADO = {
    ("GET", "/login"): None,
    ("POST", "/login"): None,
    ("GET", "/"): "rota:/",
    ("POST", "/logout"): "rota:/logout",
    ("GET", "/perfil/alterar-senha"): "rota:/perfil/alterar-senha",
    ("POST", "/perfil/alterar-senha"): "rota:/perfil/alterar-senha",
    ("GET", "/admin"): "rota:/admin",
    ("GET", "/revisor"): "rota:/revisor",
    ("GET", "/admin/obras"): "rota:/admin/obras",
    ("GET", "/admin/obras/nova"): "rota:/admin/obras",
    ("POST", "/admin/obras"): "rota:/admin/obras",
    ("GET", "/admin/obras/{obra_id}"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/liberar"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/alterar"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/reenviar"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/aceitar"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/dispensar"): "rota:/admin/obras",
    ("POST", "/admin/obras/{obra_id}/cancelar"): "rota:/admin/obras",
    ("GET", "/revisor/obras"): "rota:/revisor/obras",
    ("GET", "/revisor/obras/{obra_id}"): "rota:/revisor/obras",
    ("POST", "/revisor/obras/{obra_id}/revisar"): "rota:/revisor/obras",
    ("POST", "/revisor/obras/{obra_id}/recusar"): "rota:/revisor/obras",
    ("POST", "/revisor/obras/{obra_id}/solicitar"): "rota:/revisor/obras",
    ("POST", "/revisor/obras/{obra_id}/posicionar"): "rota:/revisor/obras",
    ("GET", "/obras"): "rota:/obras",
    ("GET", "/obras/{obra_id}"): "rota:/obras",
    ("GET", "/aluno"): "rota:/aluno",
    ("GET", "/aluno/licao/{study_id}"): "rota:/aluno/licao",
    ("POST", "/aluno/licao/{study_id}"): "rota:/aluno/licao",
}

# HTTP esperado, fixo. Nao consulte pode(): o teste repetiria a matriz.
LIBERADOS = {
    ("GET", "/"): {
        Role.ADMIN,
        Role.REVISOR,
        Role.COORDENADOR,
        Role.INSTRUTOR,
        Role.ALUNO,
    },
    ("GET", "/perfil/alterar-senha"): {
        Role.ADMIN,
        Role.REVISOR,
        Role.COORDENADOR,
        Role.INSTRUTOR,
        Role.ALUNO,
    },
    ("GET", "/admin"): {Role.ADMIN},
    ("GET", "/admin/obras"): {Role.ADMIN},
    ("GET", "/admin/obras/nova"): {Role.ADMIN},
    ("GET", "/revisor"): {Role.REVISOR},
    ("GET", "/revisor/obras"): {Role.REVISOR},
    ("GET", "/obras"): {Role.ADMIN, Role.REVISOR},
    ("GET", "/aluno"): {
        Role.ADMIN,
        Role.REVISOR,
        Role.COORDENADOR,
        Role.INSTRUTOR,
        Role.ALUNO,
    },
}

PAPEIS_DO_LOGOUT = (
    Role.ADMIN,
    Role.REVISOR,
    Role.COORDENADOR,
    Role.INSTRUTOR,
    Role.ALUNO,
)


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
    assert PERMISSOES["rota:/logout"] == PAPEIS_DO_LOGOUT
    assert Role.ALUNO not in PERMISSOES["rota:/admin"]
    assert Role.REVISOR not in PERMISSOES["rota:/admin"]
    assert Role.ADMIN in PERMISSOES["rota:/admin"]
    assert PERMISSOES["rota:/revisor"] == (Role.REVISOR,)


def test_rf02_invariante_casa_v1():
    """Mapa da v1: cada papel pode a propria casa quando a chave existe."""
    from gsi_ebd.utils.rbac import home_do_papel, home_do_papel_v1, pode

    assert home_do_papel(Role.REVISOR) == "/admin"
    assert home_do_papel_v1(Role.REVISOR) == "/revisor"
    for papel in Role:
        casa = home_do_papel_v1(papel)
        chave = "rota:" + casa
        if chave in PERMISSOES:
            assert pode(chave, papel), f"{papel.name} nao pode a casa v1 {casa}"


@pytest.mark.parametrize("papel", list(Role))
@pytest.mark.parametrize(
    "metodo,rota",
    [item for item in ESPERADO if item[0] == "GET" and "{" not in item[1]],
)
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
    if papel in LIBERADOS[(metodo, rota)]:
        assert resposta.status_code == 200, resposta.text
        assert "Didasko" in resposta.text
        assert f'data-rota="{rota}"' in resposta.text
    else:
        assert resposta.status_code == 403


def test_rf02_aluno_recebe_403_na_rota_admin(sistema):
    """O ALUNO nao passa em rota:/admin. Sem o pode() no exigir, este teste falha."""
    app = sistema["app"]

    @app.get("/sonda-admin")
    def sonda(usuario: User = Depends(exigir("rota:/admin"))):
        return PlainTextResponse(f"ok:{int(usuario.role)}")

    client = sistema["client"]
    anonimo = client.get("/sonda-admin", follow_redirects=False)
    assert anonimo.status_code in {401, 403}

    entrar(client, Role.ALUNO)
    aluno = client.get("/sonda-admin", follow_redirects=False)
    assert aluno.status_code == 403

    entrar(client, Role.ADMIN)
    admin = client.get("/sonda-admin", follow_redirects=False)
    assert admin.status_code == 200
    assert admin.text == f"ok:{int(Role.ADMIN)}"


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
