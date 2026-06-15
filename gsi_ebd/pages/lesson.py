import reflex as rx
from ..states.aluno import AlunoState
from ..components.navbar import navbar
from ..components.sidebar import sidebar
from ..components.progress_tracker import progress_tracker


def lesson_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.hstack(
                rx.button("< Voltar", on_click=rx.redirect("/aluno"), variant="ghost"),
                rx.heading("Estudo em Andamento", size="5"),
                spacing="3",
            ),
            progress_tracker(
                AlunoState.score,
                AlunoState.streak,
                AlunoState.total_answered,
                AlunoState.correct_count,
            ),
            rx.card(
                rx.vstack(
                    rx.markdown(AlunoState.study_content),
                    rx.divider(),
                    rx.cond(
                        AlunoState.current_question_idx < len(AlunoState.study_questions),
                        _lesson_question(),
                        rx.vstack(
                            rx.heading("Estudo Concluido!", color="green"),
                            rx.text(f"Pontuacao: {AlunoState.score:.0f}%"),
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
        navbar(),
        spacing="0",
        width="100%",
        height="100vh",
    )


def _lesson_question():
    return rx.vstack(
        rx.text(
            f"Pergunta {AlunoState.current_question_idx + 1}",
            font_weight="bold",
            color="gray",
        ),
        rx.input(
            placeholder="Sua resposta",
            value=AlunoState.user_answer,
            on_change=AlunoState.set_user_answer,
            size="lg",
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
            rx.callout(AlunoState.answer_feedback, variant="soft"),
        ),
        spacing="3",
        width="100%",
    )
