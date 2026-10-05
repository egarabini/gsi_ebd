import reflex as rx
from ..states.aluno import AlunoState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def aluno_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.heading("Meus Estudos", size="7", color="#1e1b4b"),
                rx.hstack(
                    rx.card(
                        rx.vstack(
                            rx.text("Pontuação", size="2", color="gray"),
                            rx.text(AlunoState.score_label, font_weight="bold", size="4"),
                            spacing="0",
                        ),
                    ),
                    rx.card(
                        rx.vstack(
                            rx.text("Sequência", size="2", color="gray"),
                            rx.text(AlunoState.streak, " dias", font_weight="bold", size="4"),
                            spacing="0",
                        ),
                    ),
                    rx.card(
                        rx.vstack(
                            rx.text("Respostas", size="2", color="gray"),
                            rx.text(
                                AlunoState.correct_count, "/", AlunoState.total_answered,
                                font_weight="bold",
                                size="4",
                            ),
                            spacing="0",
                        ),
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.cond(
                    AlunoState.has_active_study,
                    _study_view(),
                    _study_list(),
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


def _study_card(s: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(s["study_title"], font_weight="bold", size="4"),
                rx.badge(s["study_category"], color_scheme="blue"),
                justify="between",
                width="100%",
            ),
            rx.text(s["version_label"], color="gray", size="1"),
            rx.button(
                "Iniciar Estudo",
                on_click=AlunoState.select_study(s["study_id"]),
                color_scheme="green",
            ),
            spacing="2",
        ),
        width="100%",
    )


def _study_list() -> rx.Component:
    return rx.vstack(
        rx.heading("Estudos Disponíveis", size="4"),
        rx.foreach(
            AlunoState.assigned_studies.to(list[dict[str, str]]),
            _study_card,
        ),
        spacing="3",
        width="100%",
    )


def _study_view():
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.heading("Licao", size="4"),
                rx.markdown(AlunoState.study_content),
                spacing="3",
            ),
            width="100%",
        ),
        rx.cond(
            AlunoState.has_more_questions,
            _question_card(),
            rx.card(
                rx.vstack(
                    rx.heading("Estudo Concluido!", size="4", color="green"),
                    rx.text(AlunoState.score_label),
                    rx.button("Voltar aos Estudos", on_click=AlunoState.load_assigned_studies, color_scheme="blue"),
                    spacing="3",
                ),
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


def _question_card():
    return rx.card(
        rx.vstack(
            rx.text(
                AlunoState.question_label,
                font_weight="bold",
                color="gray",
            ),
            rx.text(
                AlunoState.current_question_text,
                size="4",
                font_weight="bold",
            ),
            rx.input(
                placeholder="Sua resposta",
                value=AlunoState.user_answer,
                on_change=AlunoState.set_user_answer,
                size="3",
            ),
            rx.cond(
                AlunoState.show_feedback,
                rx.callout(
                    AlunoState.answer_feedback,
                    variant="soft",
                    color_scheme=AlunoState.feedback_color,
                ),
            ),
            rx.hstack(
                rx.button(
                    "Responder",
                    on_click=AlunoState.submit_answer,
                    color_scheme="blue",
                ),
                rx.cond(
                    AlunoState.show_feedback,
                    rx.button("Proxima", on_click=AlunoState.next_question, color_scheme="green"),
                ),
                spacing="3",
            ),
            spacing="3",
        ),
        width="100%",
    )
