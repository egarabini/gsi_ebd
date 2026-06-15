import reflex as rx
from ..models.user import Role
from ..states.auth import AuthState


def sidebar() -> rx.Component:
    items = rx.cond(
        AuthState.is_admin,
        _admin_items(),
        rx.cond(
            AuthState.is_supervisor,
            _supervisor_items(),
            rx.cond(
                AuthState.is_gestor,
                _gestor_items(),
                _aluno_items(),
            ),
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


def _sidebar_item(icon_name: str, label: str, href: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(icon_name, size=18),
            rx.text(label, display=CommonState.sidebar_open if True else "none"),
            spacing="2",
            align="center",
            padding="0.5rem",
            border_radius="0.375rem",
            _hover={"bg": "var(--accent-4)"},
            width="100%",
        ),
        href=href,
        width="100%",
    )


def _admin_items():
    return rx.fragment(
        _sidebar_item("shield", "Admin", "/admin"),
        _sidebar_item("users", "Gestores", "/admin/gestores"),
        _sidebar_item("eye", "Supervisores", "/admin/supervisores"),
        _sidebar_item("bar-chart-2", "Relatorios", "/admin/relatorios"),
    )


def _supervisor_items():
    return rx.fragment(
        _sidebar_item("eye", "Visao Geral", "/supervisor"),
        _sidebar_item("bar-chart-2", "Relatorios", "/supervisor/relatorios"),
    )


def _gestor_items():
    return rx.fragment(
        _sidebar_item("home", "Dashboard", "/gestor"),
        _sidebar_item("users", "Alunos", "/gestor/alunos"),
        _sidebar_item("book-open", "Estudos", "/gestor/estudos"),
        _sidebar_item("bar-chart-2", "Progresso", "/gestor/progresso"),
    )


def _aluno_items():
    return rx.fragment(
        _sidebar_item("home", "Inicio", "/aluno"),
        _sidebar_item("book-open", "Estudos", "/aluno/estudos"),
        _sidebar_item("trophy", "Progresso", "/aluno/progresso"),
    )


from ..states.common import CommonState
