import reflex as rx
from ..states.coordenador import CoordenadorState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def coordenador_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.heading("Painel do Coordenador", size="6"),
                _metricas(),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Turmas", value="turmas"),
                        rx.tabs.trigger("Alunos", value="alunos"),
                        rx.tabs.trigger("Atribuir Estudo", value="atribuir"),
                    ),
                    rx.tabs.content(_turmas_tab(), value="turmas"),
                    rx.tabs.content(_alunos_tab(), value="alunos"),
                    rx.tabs.content(_atribuir_tab(), value="atribuir"),
                    default_value="turmas",
                    width="100%",
                ),
                spacing="4",
                padding="2rem",
                width="100%",
                overflow_y="auto",
                height="calc(100vh - 52px)",
            ),
            spacing="0",
            width="100%",
        ),
        spacing="0",
        width="100%",
        height="100vh",
    )


def _metricas():
    return rx.hstack(
        _metrica_card("Alunos", CoordenadorState.total_alunos, "users"),
        _metrica_card("Progresso Medio", CoordenadorState.media_progresso, "trending-up"),
        _metrica_card("Pendencias", CoordenadorState.pendencias, "clock"),
        spacing="4",
        width="100%",
    )


def _metrica_card(label: str, value, icon_name: str):
    return rx.card(
        rx.hstack(
            rx.icon(icon_name, size=20),
            rx.vstack(
                rx.text(label, size="2", color="gray"),
                rx.text(value, size="5", font_weight="bold"),
                spacing="0",
            ),
            spacing="3",
            align="center",
        ),
        width="100%",
    )


def _turma_card(t):
    return rx.card(
        rx.hstack(
            rx.text(t.nome, font_weight="bold"),
            rx.text(t.descricao, color="gray"),
            rx.spacer(),
            rx.badge(rx.cond(t.is_active, "Ativa", "Inativa"), color_scheme="green"),
            justify="between",
            width="100%",
        ),
    )


def _turmas_tab():
    return rx.vstack(
        rx.cond(
            CoordenadorState.turmas,
            rx.foreach(CoordenadorState.turmas, _turma_card),
            rx.text("Nenhuma turma atribuida a este coordenador ainda."),
        ),
        spacing="3",
        width="100%",
    )


def _aluno_card(a):
    return rx.card(
        rx.hstack(
            rx.text(a.nome_completo, font_weight="bold"),
            rx.text(a.email, color="gray"),
            rx.spacer(),
            rx.badge("Ativo", color_scheme="green"),
            justify="between",
            width="100%",
        ),
    )


def _aluno_checkbox(a):
    return rx.checkbox(
        a.nome_completo,
        on_change=lambda: CoordenadorState.toggle_aluno_selection(a.id),
    )


def _alunos_tab():
    return rx.vstack(
        rx.cond(
            CoordenadorState.alunos,
            rx.foreach(CoordenadorState.alunos, _aluno_card),
            rx.text("Nenhum aluno nas turmas deste coordenador ainda."),
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
                    CoordenadorState.study_options,
                    placeholder="Selecione um estudo",
                    value=CoordenadorState.selected_study_option,
                    on_change=CoordenadorState.set_selected_study_option,
                    width="100%",
                ),
                rx.text("Selecione os alunos:"),
                rx.foreach(CoordenadorState.alunos, _aluno_checkbox),
                rx.button("Atribuir", on_click=CoordenadorState.assign_study, color_scheme="blue"),
                rx.cond(
                    CoordenadorState.message != "",
                    rx.callout(CoordenadorState.message, variant="soft", color_scheme=CoordenadorState.message_type),
                ),
                spacing="3",
            ),
            width="100%",
        ),
        spacing="3",
        width="100%",
    )
