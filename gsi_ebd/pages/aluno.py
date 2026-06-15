import reflex as rx
from ..states.aluno import AlunoState
from ..components.navbar import navbar
from ..components.sidebar import sidebar
from ..components.progress_tracker import progress_tracker


def aluno_page() -> rx.Component:
    return rx.hstack(
        sidebar(),
        rx.vstack(
            rx.heading("Meus Estudos", size="6"),
            progress_tracker(
                AlunoState.score,
                AlunoState.streak,
                AlunoState.total_answered,
                AlunoState.correct_count,
            ),
            rx.cond(
                AlunoState.current_study_id is not None,
                _study_view(),
                _study_list(),
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


def _study_list():
    return rx.vstack(
        rx.heading("Estudos Disponiveis", size="4"),
        rx.foreach(
            AlunoState.assigned_studies,
            lambda s: rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.text(s["study_title"], font_weight="bold", size="4"),
                        rx.badge(s["study_category"], color_scheme="blue"),
                        justify="between",
                        width="100%",
                    ),
                    rx.text(f"Versao {s['version']}", color="gray", font_size="sm"),
                    rx.button(
                        "Iniciar Estudo",
                        on_click=lambda: AlunoState.start_study(s["study_id"], s["version_id"]),
                        color_scheme="green",
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
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
            AlunoState.current_question_idx < len(AlunoState.study_questions),
            _question_card(),
            rx.card(
                rx.vstack(
                    rx.heading("Estudo Concluido!", size="4", color="green"),
                    rx.text(f"Pontuacao final: {AlunoState.score:.0f}%"),
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
    q_idx = AlunoState.current_question_idx
    return rx.card(
        rx.vstack(
            rx.text(
                f"Pergunta {q_idx + 1} de {len(AlunoState.study_questions)}",
                font_weight="bold",
                color="gray",
            ),
            rx.cond(
                AlunoState.study_questions.length() > 0,
                rx.text(
                    AlunoState.study_questions[q_idx]["question"] if AlunoState.study_questions else "",
                    size="4",
                    font_weight="bold",
                ),
                rx.text(""),
            ),
            rx.cond(
                AlunoState.study_questions.length() > 0,
                rx.cond(
                    AlunoState.study_questions[q_idx].get("type", "") == "multiple_choice",
                    rx.radio_group(
                        AlunoState.study_questions[q_idx].get("options", []) if AlunoState.study_questions else [],
                        on_change=AlunoState.set_user_answer,
                    ),
                    rx.input(
                        placeholder="Sua resposta",
                        value=AlunoState.user_answer,
                        on_change=AlunoState.set_user_answer,
                    ),
                ),
                rx.text(""),
            ),
            rx.cond(
                AlunoState.show_feedback,
                rx.callout(
                    AlunoState.answer_feedback,
                    variant="soft",
                    color_scheme="green" if AlunoState.streak > 0 else "red",
                ),
            ),
            rx.hstack(
                rx.button(
                    "Responder",
                    on_click=AlunoState.submit_answer,
                    disabled=AlunoState.show_feedback,
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
