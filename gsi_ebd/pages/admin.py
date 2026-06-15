import reflex as rx
from ..states.admin import AdminState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def admin_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.heading("Painel do Administrador", size="6"),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Gestores", value="gestores"),
                    rx.tabs.trigger("Supervisores", value="supervisores"),
                ),
                rx.tabs.content(_gestores_tab(), value="gestores"),
                rx.tabs.content(_supervisores_tab(), value="supervisores"),
                default_value="gestores",
                width="100%",
            ),
            spacing="4",
            padding="2rem",
            width="100%",
            overflow_y="auto",
            height="calc(100vh - 52px)",
        ),
        navbar(),
        spacing="0",
        width="100%",
        height="100vh",
    )


def _gestor_card(g):
    return rx.card(
        rx.hstack(
            rx.text(g.nome, font_weight="bold"),
            rx.text(g.email, color="gray"),
            rx.spacer(),
            rx.cond(
                g.is_active,
                rx.badge("Ativo", color_scheme="green"),
                rx.badge("Inativo", color_scheme="red"),
            ),
            rx.cond(
                g.is_active,
                rx.button("Desativar", on_click=lambda: AdminState.deactivate_user(g.id), size="1", variant="outline", color_scheme="red"),
                rx.text(""),
            ),
            justify="between",
            width="100%",
        ),
    )


def _gestores_tab():
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.heading("Novo Gestor", size="4"),
                rx.input(placeholder="Nome", value=AdminState.new_gestor_nome, on_change=AdminState.set_new_gestor_nome),
                rx.input(placeholder="Email", value=AdminState.new_gestor_email, on_change=AdminState.set_new_gestor_email, type="email"),
                rx.input(placeholder="Senha", value=AdminState.new_gestor_password, on_change=AdminState.set_new_gestor_password, type="password"),
                rx.button("Criar Gestor", on_click=AdminState.create_gestor, color_scheme="blue"),
                rx.cond(
                    AdminState.message != "",
                    rx.callout(AdminState.message, variant="soft", color_scheme=AdminState.message_type),
                ),
                spacing="3",
            ),
            width="100%",
        ),
        rx.divider(),
        rx.heading("Gestores Cadastrados", size="4"),
        rx.foreach(AdminState.gestores, _gestor_card),
        spacing="3",
        width="100%",
    )


def _supervisor_card(s):
    return rx.card(
        rx.hstack(
            rx.text(s.nome, font_weight="bold"),
            rx.text(s.email, color="gray"),
            rx.spacer(),
            rx.cond(
                s.is_active,
                rx.badge("Ativo", color_scheme="green"),
                rx.badge("Inativo", color_scheme="red"),
            ),
            justify="between",
            width="100%",
        ),
    )


def _supervisores_tab():
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.heading("Novo Supervisor", size="4"),
                rx.input(placeholder="Nome", value=AdminState.new_supervisor_nome, on_change=AdminState.set_new_supervisor_nome),
                rx.input(placeholder="Email", value=AdminState.new_supervisor_email, on_change=AdminState.set_new_supervisor_email, type="email"),
                rx.input(placeholder="Senha", value=AdminState.new_supervisor_password, on_change=AdminState.set_new_supervisor_password, type="password"),
                rx.button("Criar Supervisor", on_click=AdminState.create_supervisor, color_scheme="blue"),
                spacing="3",
            ),
            width="100%",
        ),
        rx.divider(),
        rx.heading("Supervisores Cadastrados", size="4"),
        rx.foreach(AdminState.supervisores, _supervisor_card),
        spacing="3",
        width="100%",
    )
