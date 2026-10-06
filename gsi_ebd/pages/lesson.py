import reflex as rx
from ..states.aluno import AlunoState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def lesson_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.hstack(
                    rx.button("< Voltar", on_click=rx.redirect("/aluno"), variant="ghost"),
                    rx.heading("Estudo em Andamento", size="5"),
                    spacing="3",
                ),
                rx.hstack(
                    rx.badge(AlunoState.score_label, color_scheme="blue", variant="soft"),
                    rx.badge(AlunoState.question_label, color_scheme="gray", variant="soft"),
                    rx.cond(
                        AlunoState.pending_review > 0,
                        rx.badge(
                            AlunoState.pending_review_label,
                            color_scheme="orange",
                            variant="soft",
                        ),
                    ),
                    spacing="2",
                ),
                rx.card(
                    rx.vstack(
                        rx.markdown(AlunoState.study_content),
                        rx.divider(),
                        rx.cond(
                            AlunoState.has_more_questions,
                            _lesson_question(),
                            rx.vstack(
                                rx.heading("Estudo Concluido!", color="green"),
                                rx.text(AlunoState.score_label),
                                rx.cond(
                                    AlunoState.pending_review > 0,
                                    rx.callout(
                                        AlunoState.pending_review_label,
                                        icon="info",
                                        color_scheme="orange",
                                        variant="soft",
                                    ),
                                ),
                                rx.button("Voltar", on_click=rx.redirect("/aluno")),
                                spacing="3",
                            ),
                        ),
                        spacing="3",
                    ),
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


def _lesson_question():
    return rx.vstack(
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
        # Contexto pedagogico: o "porque" da questao, no estilo do estudo
        # que originou o GSI-EBD (passagem + explicacao junto da pergunta).
        rx.cond(
            AlunoState.current_question_context != "",
            rx.callout(
                rx.markdown(AlunoState.current_question_context),
                icon="book-open",
                color_scheme="gray",
                variant="surface",
            ),
        ),
        rx.text_area(
            placeholder="Escreva sua resposta",
            value=AlunoState.user_answer,
            on_change=AlunoState.set_user_answer,
            rows="3",
            width="100%",
        ),
        rx.hstack(
            rx.button("Enviar", on_click=AlunoState.submit_answer, color_scheme="blue"),
            rx.cond(
                AlunoState.show_feedback,
                rx.button("Proxima", on_click=AlunoState.next_question, color_scheme="green"),
            ),
            spacing="3",
        ),
        rx.cond(
            AlunoState.show_feedback,
            rx.callout(AlunoState.answer_feedback, variant="soft", color_scheme=AlunoState.feedback_color),
        ),
        spacing="3",
        width="100%",
    )
