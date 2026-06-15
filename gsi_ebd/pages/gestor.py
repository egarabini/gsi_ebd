import reflex as rx
from ..states.gestor import GestorState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def gestor_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.heading("Painel do Gestor", size="6"),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Alunos", value="alunos"),
                    rx.tabs.trigger("Atribuir Estudo", value="atribuir"),
                ),
                rx.tabs.content(_alunos_tab(), value="alunos"),
                rx.tabs.content(_atribuir_tab(), value="atribuir"),
                default_value="alunos",
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


def _alunos_tab():
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.heading("Novo Aluno", size="4"),
                rx.input(placeholder="Nome", value=GestorState.new_aluno_nome, on_change=GestorState.set_new_aluno_nome),
                rx.input(placeholder="Email", value=GestorState.new_aluno_email, on_change=GestorState.set_new_aluno_email, type="email"),
                rx.input(placeholder="Senha", value=GestorState.new_aluno_password, on_change=GestorState.set_new_aluno_password, type="password"),
                rx.button("Criar Aluno", on_click=GestorState.create_aluno, color_scheme="blue"),
                rx.cond(
                    GestorState.message != "",
                    rx.callout(GestorState.message, variant="soft", color_scheme=GestorState.message_type),
                ),
                spacing="3",
            ),
            width="100%",
        ),
        rx.divider(),
        rx.heading("Meus Alunos", size="4"),
        rx.foreach(
            GestorState.alunos,
            lambda a: rx.card(
                rx.hstack(
                    rx.text(a.nome, font_weight="bold"),
                    rx.text(a.email, color="gray"),
                    rx.spacer(),
                    rx.badge("Ativo", color_scheme="green"),
                    justify="between",
                    width="100%",
                ),
            ),
        ),
        spacing="3",
        width="100%",
    )


def _atribuir_tab():
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.heading("Atribuir Estudo", size="4"),
                rx.select(
                    [s["title"] for s in []],
                    placeholder="Selecione um estudo",
                    on_change=GestorState.set_selected_study_id,
                    width="100%",
                ),
                rx.text("Selecione os alunos:"),
                rx.foreach(
                    GestorState.alunos,
                    lambda a: rx.checkbox(
                        a.nome,
                        on_change=lambda: GestorState.toggle_aluno_selection(a.id),
                    ),
                ),
                rx.button("Atribuir", on_click=GestorState.assign_study, color_scheme="blue"),
                rx.cond(
                    GestorState.message != "",
                    rx.callout(GestorState.message, variant="soft", color_scheme=GestorState.message_type),
                ),
                spacing="3",
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
    )
