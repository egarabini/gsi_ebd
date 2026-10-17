import reflex as rx

from ..states.admin import AdminState
from ..states.auth import AuthState
from ..states.common import CommonState


def sidebar() -> rx.Component:
    items = rx.cond(
        AuthState.is_admin,
        _admin_items(),
        rx.cond(
            AuthState.is_coordenador,
            _coordenador_items(),
            _aluno_items(),
        ),
    )
    return rx.box(
        rx.vstack(
            items,
            spacing="2",
            padding="1rem",
            width="100%",
        ),
        width=CommonState.sidebar_width,
        bg="var(--accent-3)",
        height="calc(100vh - 52px)",
        position="sticky",
        top="52px",
        transition="width 0.2s",
        overflow="hidden",
        border_right=f"1px solid var(--accent-5)",
    )


def _item_body(icon_name: str, label: str) -> rx.Component:
    return rx.hstack(
        rx.icon(icon_name, size=18),
        rx.text(label, display=rx.cond(CommonState.sidebar_open, "block", "none")),
        spacing="2",
        align="center",
        padding="0.5rem",
        border_radius="0.375rem",
        _hover={"bg": "var(--accent-4)"},
        width="100%",
    )


def _sidebar_item(icon_name: str, label: str, href: str) -> rx.Component:
    return rx.link(_item_body(icon_name, label), href=href, width="100%")


def _sidebar_tab_item(icon_name: str, label: str, aba: str) -> rx.Component:
    """Item que leva a /admin E abre a aba correspondente.

    Antes todos os itens do admin apontavam para /admin sem selecionar aba — o
    menu parecia funcionar e nao fazia nada, e dois itens tinham o mesmo rotulo.
    """
    return rx.link(
        _item_body(icon_name, label),
        href="/admin",
        on_click=AdminState.set_tab_atual(aba),
        width="100%",
    )


def _admin_items():
    return rx.fragment(
        _sidebar_tab_item("users", "Gestores", "gestores"),
        _sidebar_tab_item("shield", "Coordenadores", "coordenadores"),
        _sidebar_tab_item("clipboard-check", "Aprovação de Estudos", "estudos"),
        _sidebar_tab_item("book-marked", "Obras", "obras"),
        _sidebar_tab_item("layers", "Estudo Aplicável", "estudo_aplicado"),
        _sidebar_tab_item("inbox", "Leads", "leads"),
        # Fora de /admin: e a tela de atribuicao, que o admin tambem usa para
        # disponibilizar estudo ao aluno (ver CoordenadorState.load_alunos).
        _sidebar_item("send", "Disponibilizar Estudos", "/coordenador"),
    )


def _coordenador_items():
    return rx.fragment(
        _sidebar_item("home", "Ambiente", "/coordenador"),
        _sidebar_item("users", "Instrutores", "/coordenador"),
        _sidebar_item("book-open", "Catalogo", "/coordenador"),
        _sidebar_item("bar-chart-2", "Progresso", "/coordenador"),
    )


def _aluno_items():
    return rx.fragment(
        _sidebar_item("home", "Inicio", "/aluno"),
        _sidebar_item("book-open", "Estudos", "/aluno"),
        _sidebar_item("trophy", "Progresso", "/aluno"),
    )
