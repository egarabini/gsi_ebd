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
    """Varre os EVENTOS reais (`event_handlers`), nao `vars(cls)`.

    O Reflex troca cada metodo publico por um `EventHandler` quando a classe e
    compilada, entao `inspect.isfunction(vars(cls)[nome])` e False. A versao
    anterior desta varredura examinava **zero** eventos e passava com os 28
    `@exige` removidos - achado do EVAL (rodada 1).
    """
    for estado in ESTADOS_GUARDADOS:
        sem_marcador = []
        for nome, handler in estado.event_handlers.items():
            if nome == "setvar" or nome.startswith("set_"):
                continue   # setters de formulario: cobertos pela lista congelada
            if not hasattr(getattr(handler, "fn", None), "__exige__"):
                sem_marcador.append(nome)
        assert sem_marcador == [], f"{estado.__name__} sem @exige: {sem_marcador}"


# ── 7. rotas publicas e casa unica (F-06 e F-08) ───────────────────────────
def test_rotas_publicas_abertas_a_todos():
    for rota in (
        "/", "/login", "/confirmar/[token]", "/homenagens",
        "/aluno", "/aluno/licao", "/aluno/pareceres", "/perfil/alterar-senha",
    ):
        for papel in Role:
            assert rbac.pode("rota:" + rota, papel), f"{papel.name} deveria poder {rota}"


def test_home_consistente_com_authservice():
    """A casa do papel tem UMA fonte: `rbac.home_do_papel`.

    Antes havia duas tabelas iguais (rbac e AuthService) - duas verdades para a
    mesma pergunta, que divergiriam na primeira mudanca.
    """
    from gsi_ebd.services.auth_service import AuthService

    for papel in Role:
        assert AuthService.redirect_for_role(papel) == rbac.home_do_papel(papel)


# ── 8. fiacao real: os on_load do app e os guardas de verdade ──────────────
def test_fiacao_on_load_das_rotas_guardadas():
    """Importa o app e confere que cada rota guardada TEM o guarda no on_load.

    Sem este teste, apagar a guarda do `on_load` nao reprovava nada (achado do
    EVAL, rodada 1).
    """
    from gsi_ebd.gsi_ebd import app

    esperado = {
        "/admin": AuthState.guarda_admin,
        "/coordenador": AuthState.guarda_coordenador,
        "/revisao": AuthState.guarda_revisao,
    }
    for rota, guarda in esperado.items():
        # Reflex 0.9.5: as paginas ficam em `_unevaluated_pages`, com a rota sem
        # a barra inicial ('admin', 'coordenador', 'revisao').
        pagina = app._unevaluated_pages[rota.lstrip("/")]
        on_load = list(getattr(pagina, "on_load", None) or [])
        funcoes = [getattr(h, "fn", None) for h in on_load]
        assert guarda.fn in funcoes, f"{rota} sem o guarda no on_load: {funcoes}"


# ── 9. a CHAVE de cada evento (nao so a presenca do marcador) ──────────────
# Sem este mapa, decorar load_leads com a chave errada (catalogo_ler) passava
# na suite e deixava o REVISOR carregar leads - achado do EVAL (rodada 2, m7).
CHAVES_ESPERADAS = {
    "AdminState": {
        "load_coordenadores": "acao:usuarios",
        "load_leads": "acao:leads",
        "load_estudos_pendentes": "acao:catalogo_ler",
        "load_obras": "acao:catalogo_ler",
        "load_estudos_aplicados": "acao:catalogo_ler",
        "create_gestor": "acao:usuarios",
        "activate_user": "acao:usuarios",
        "suspend_user": "acao:usuarios",
        "cancel_user": "acao:usuarios",
        "update_lead_status": "acao:leads",
        "aprovar_estudo": "acao:catalogo_aprovar",
        "aprovar_todos": "acao:catalogo_aprovar",
        "rejeitar_estudo": "acao:catalogo_aprovar",
    },
    "CoordenadorState": {
        n: "acao:coordenacao"
        for n in ("load_all", "load_alunos", "load_estudos", "load_turmas",
                  "toggle_aluno", "select_all_alunos", "clear_selection", "assign_study")
    },
    "RevisaoState": {
        n: "acao:revisao"
        for n in ("load_fila", "abrir_resposta", "fechar_resposta", "pedir_sugestao",
                  "usar_sugestao", "descartar_sugestao", "salvar_parecer")
    },
}


@pytest.mark.parametrize("nome", sorted(CHAVES_ESPERADAS))
def test_chave_de_cada_evento(nome):
    estado = next(e for e in ESTADOS if e.__name__ == nome)
    reais = {
        n: getattr(getattr(h, "fn", None), "__exige__", None)
        for n, h in estado.event_handlers.items()
        if n != "setvar" and not n.startswith("set_")
    }
    esperado = CHAVES_ESPERADAS[nome]
    diff = {k: (reais.get(k), esperado.get(k)) for k in set(reais) | set(esperado) if reais.get(k) != esperado.get(k)}
    assert not diff, f"{nome}: chave errada em {diff} (real, esperado)"


# ── 10. handlers REAIS barrados nao executam ───────────────────────────────
def test_handlers_reais_barrados_nao_executam():
    """Chama o handler de verdade (fn) com papel negado: devolve None e nao toca banco.

    O caminho negado do @exige retorna antes do corpo - nenhuma sessao aberta.
    """
    from types import SimpleNamespace

    casos = (
        (AdminState.aprovar_estudo, Role.REVISOR),
        (AdminState.aprovar_todos, Role.REVISOR),
        (AdminState.rejeitar_estudo, Role.REVISOR),
        (AdminState.activate_user, Role.REVISOR),
        (AdminState.update_lead_status, Role.ALUNO),
        (AdminState.load_leads, Role.ALUNO),
        (CoordenadorState.assign_study, Role.ALUNO),
        (RevisaoState.salvar_parecer, Role.COORDENADOR),
    )
    for handler, papel in casos:
        falso = SimpleNamespace(current_user_role=papel)
        assert handler.fn(falso, 1) is None, f"{handler.fn.__name__} executou para {papel.name}"


# ── 11. o guarda de rota: destino do redirect asserido ────────────────────
def _destino(event_spec):
    """Extrai o path do EventSpec devolvido por rx.redirect."""
    for _var, valor in event_spec.args:
        valor_str = getattr(valor, "_var_value", None)
        if isinstance(valor_str, str):
            return valor_str
    return None


def test_guarda_real_bloqueia_e_libera():
    """O guarda que o app USA barra e libera, e o redirect vai para a CASA do papel.

    Tabela hardcoded de proposito: se o teste usasse `home_do_papel` como oraculo,
    trocar a casa por /login passaria (achado do EVAL, rodada 2, mutacao m6).
    """
    from types import SimpleNamespace

    casas = {
        Role.ADMIN: "/admin",
        Role.REVISOR: "/admin",
        Role.COORDENADOR: "/coordenador",
        Role.INSTRUTOR: "/revisao",
        Role.ALUNO: "/aluno",
    }
    casos = (
        ("/admin", AuthState.guarda_admin),
        ("/coordenador", AuthState.guarda_coordenador),
        ("/revisao", AuthState.guarda_revisao),
    )
    for rota, handler in casos:
        fn = handler.fn
        anon = SimpleNamespace(is_authenticated=False, current_user_role=Role.ALUNO)
        assert _destino(fn(anon)) == "/login", f"{rota}: anonimo deveria ir ao login"
        for papel in Role:
            falso = SimpleNamespace(is_authenticated=True, current_user_role=papel)
            resultado = fn(falso)
            if papel in rbac.PERMISSOES["rota:" + rota]:
                assert resultado is None, f"{rota}: {papel.name} deveria passar"
            else:
                assert _destino(resultado) == casas[papel], (
                    f"{rota}: {papel.name} deveria ir para {casas[papel]}, foi {_destino(resultado)}"
                )


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
