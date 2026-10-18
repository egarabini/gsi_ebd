"""Guarda de papel (DEM-202610-002).

Roda do diretorio do app (`ESTUDOS_BIBLICOS/GSI_EBD`): o Reflex descobre o
`rxconfig.py` a partir do CWD. De outro diretorio a config nao e lida e os
setters explicitos nem resolvem - os 9 casos de `test_paginas` falham.

Cobre: matriz (rotas e acoes), invariante da casa do papel, ausencia de setter de
identidade em TODOS os estados, lista de eventos congelada (evento novo falha ate
ser classificado) e o marcador `__exige__` em todo evento dos 3 estados
administrativos.
"""
import inspect

import pytest

from gsi_ebd.models.user import Role
from gsi_ebd.utils import rbac

# ── estados do projeto (7) ──────────────────────────────────────────────────
from gsi_ebd.states.admin import AdminState
from gsi_ebd.states.aluno import AlunoState
from gsi_ebd.states.auth import AuthState
from gsi_ebd.states.common import CommonState
from gsi_ebd.states.coordenador import CoordenadorState
from gsi_ebd.states.perfil import PerfilState
from gsi_ebd.states.revisao import RevisaoState

ESTADOS = (AuthState, AdminState, CoordenadorState, RevisaoState, AlunoState, PerfilState, CommonState)
ESTADOS_GUARDADOS = (AdminState, CoordenadorState, RevisaoState)

IDENTIDADE = (
    "current_user_id",
    "current_user_name",
    "current_user_role",
    "current_user_status",
    "current_user_ambiente",
    "is_authenticated",
    "must_change_password",
)

# ── lista congelada de eventos (evento novo falha o build) ──────────────────
FROZEN = {
    "AuthState": [
        "check_auth", "confirm_account_token", "dismiss_status_modal", "guarda_admin",
        "guarda_coordenador", "guarda_revisao", "is_instrutor", "login", "logout",
        "request_reactivation", "set_login_email", "set_login_password", "setvar",
    ],
    "AdminState": [
        "activate_user", "aprovar_estudo", "aprovar_todos", "cancel_user", "create_gestor",
        "load_coordenadores", "load_estudos_aplicados", "load_estudos_pendentes", "load_leads",
        "load_obras", "rejeitar_estudo", "set_new_gestor_email", "set_new_gestor_nome",
        "set_reject_motivo", "set_tab_atual", "setvar", "suspend_user", "update_lead_status",
    ],
    "CoordenadorState": [
        "assign_study", "clear_selection", "load_all", "load_alunos", "load_estudos",
        "load_turmas", "select_all_alunos", "set_selected_study_option", "setvar", "toggle_aluno",
    ],
    "RevisaoState": [
        "abrir_resposta", "descartar_sugestao", "fechar_resposta", "load_fila",
        "pedir_sugestao", "salvar_parecer", "set_considerou_correto", "set_parecer_texto",
        "setvar", "usar_sugestao",
    ],
    "AlunoState": [
        "load_assigned_studies", "load_pareceres", "next_question", "select_study",
        "set_user_answer", "setvar", "start_study", "submit_answer",
    ],
    "PerfilState": [
        "alterar_senha", "check_perfil_auth", "set_confirma_senha", "set_nova_senha",
        "set_senha_atual", "setvar",
    ],
    "CommonState": ["setvar", "toggle_sidebar"],
}


# ── 1. matriz de rotas ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "rota,permitidos,negados",
    [
        ("/admin", (Role.ADMIN, Role.REVISOR), (Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)),
        ("/coordenador", (Role.ADMIN, Role.COORDENADOR), (Role.REVISOR, Role.INSTRUTOR, Role.ALUNO)),
        ("/revisao", (Role.ADMIN, Role.INSTRUTOR), (Role.REVISOR, Role.COORDENADOR, Role.ALUNO)),
    ],
)
def test_matriz_de_rotas(rota, permitidos, negados):
    for papel in permitidos:
        assert rbac.pode("rota:" + rota, papel), f"{papel.name} deveria poder {rota}"
    for papel in negados:
        assert not rbac.pode("rota:" + rota, papel), f"{papel.name} NAO deveria poder {rota}"


# ── 2. matriz de acoes ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "acao,permitidos,negados",
    [
        ("acao:catalogo_ler", (Role.ADMIN, Role.REVISOR), (Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)),
        ("acao:catalogo_aprovar", (Role.ADMIN,), (Role.REVISOR, Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)),
        ("acao:usuarios", (Role.ADMIN,), (Role.REVISOR, Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)),
        ("acao:leads", (Role.ADMIN,), (Role.REVISOR, Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)),
        ("acao:coordenacao", (Role.ADMIN, Role.COORDENADOR), (Role.REVISOR, Role.INSTRUTOR, Role.ALUNO)),
        ("acao:revisao", (Role.ADMIN, Role.INSTRUTOR), (Role.REVISOR, Role.COORDENADOR, Role.ALUNO)),
    ],
)
def test_matriz_de_acoes(acao, permitidos, negados):
    for papel in permitidos:
        assert rbac.pode(acao, papel), f"{papel.name} deveria poder {acao}"
    for papel in negados:
        assert not rbac.pode(acao, papel), f"{papel.name} NAO deveria poder {acao}"


def test_chave_desconhecida_nega():
    assert not rbac.pode("rota:/nao-existe", Role.ADMIN)
    assert not rbac.pode("acao:nao-existe", Role.ADMIN)
    assert not rbac.pode("", Role.ADMIN)


def test_invariante_casa_do_papel():
    """A casa de cada papel nao pode ser NEGADA por uma guarda - senao o redirect faz loop.

    Rota fora de PERMISSOES nao tem guarda (ex.: /aluno e /perfil, abertas a quem
    esta logado); a invariante so vale para as rotas guardadas.
    """
    for papel in Role:
        casa = rbac.home_do_papel(papel)
        if casa == "/login":
            continue
        chave = "rota:" + casa
        if chave in rbac.PERMISSOES:
            assert rbac.pode(chave, papel), f"{papel.name} nao pode a propria casa {casa}"


# ── 3. o cliente nao escreve a propria identidade ──────────────────────────
def test_state_auto_setters_desligado():
    """Prova que o rxconfig foi lido: sem isso os setters de identidade voltam."""
    from reflex.config import get_config

    assert get_config().state_auto_setters is False


def test_nenhum_setter_de_identidade():
    for estado in ESTADOS:
        eventos = set(estado.event_handlers)
        proibidos = [
            e for e in eventos
            if e.startswith("set_current_user") or e in ("set_is_authenticated", "set_must_change_password")
        ]
        assert proibidos == [], f"{estado.__name__} expoe {proibidos}"
        for campo in IDENTIDADE:
            assert getattr(estado, "set_" + campo, None) is None, (
                f"{estado.__name__}.set_{campo} existe - setter de identidade"
            )


# ── 4. lista de eventos congelada ──────────────────────────────────────────
@pytest.mark.parametrize("nome", sorted(FROZEN))
def test_lista_de_eventos_congelada(nome):
    """Evento novo (inclusive setter) falha ate ser classificado e a lista atualizada."""
    estado = next(e for e in ESTADOS if e.__name__ == nome)
    assert sorted(estado.event_handlers) == FROZEN[nome]


# ── 5. todo evento dos estados administrativos tem @exige ──────────────────
def test_todo_evento_tem_marcador_exige():
    for estado in ESTADOS_GUARDADOS:
        sem_marcador = []
        for nome, fn in vars(estado).items():
            if nome.startswith("_") or nome == "setvar" or not inspect.isfunction(fn):
                continue
            if nome.startswith("set_"):   # campo de formulario: coberto pela lista congelada
                continue
            if not hasattr(fn, "__exige__"):
                sem_marcador.append(nome)
        assert sem_marcador == [], f"{estado.__name__} sem @exige: {sem_marcador}"


# ── 6. o decorador realmente barra ─────────────────────────────────────────
def test_exige_barra_quem_nao_pode():
    chamadas = []

    @rbac.exige("acao:usuarios")
    def evento(self, valor):
        chamadas.append(valor)
        return "executou"

    class SemPapel:
        current_user_role = Role.ALUNO

    class ComPapel:
        current_user_role = Role.ADMIN

    assert evento(SemPapel(), 1) is None
    assert chamadas == []
    assert evento(ComPapel(), 2) == "executou"
    assert chamadas == [2]
    assert evento.__exige__ == "acao:usuarios"


def test_guarda_rota_redireciona_e_libera():
    @rbac.guarda_rota("/admin")
    def on_load(self):
        return None

    class Anonimo:
        is_authenticated = False
        current_user_role = Role.ALUNO

    class Aluno:
        is_authenticated = True
        current_user_role = Role.ALUNO

    class Revisor:
        is_authenticated = True
        current_user_role = Role.REVISOR

    assert on_load(Anonimo()) is not None   # manda para /login
    assert on_load(Aluno()) is not None     # devolve para a casa (nunca para /admin)
    assert on_load(Revisor()) is None       # revisor entra: 9.2a
