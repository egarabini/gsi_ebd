import reflex as rx


def progress_tracker(score: float, streak: int, total: int, correct: int) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Pontuacao", font_weight="bold"),
            rx.text(f"{score:.0f}%", font_size="2xl", color="var(--accent-9)"),
            justify="between",
            width="100%",
        ),
        rx.progress(value=score, width="100%", color_scheme="blue"),
        rx.hstack(
            rx.badge(f"Streak: {streak}", color_scheme="green"),
            rx.badge(f"{correct}/{total} corretas", color_scheme="blue"),
            spacing="2",
        ),
        spacing="2",
        width="100%",
        padding="1rem",
        border_radius="0.5rem",
        bg="var(--accent-2)",
    )
