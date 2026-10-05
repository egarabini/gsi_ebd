"""Seção Testemunhos — depoimentos dinâmicos via banco de dados."""
import reflex as rx


def testemunhos_section(state_cls) -> rx.Component:
    """
    Recebe a classe de State (LandingState) diretamente.
    Os testemunhos são armazenados como list[dict] no state.
    """
    return rx.box(
        rx.vstack(
            rx.badge("Depoimentos", color_scheme="violet", variant="soft", size="2"),
            rx.heading("O que dizem nossos alunos", size="7", color="#1e1b4b", text_align="center"),
            rx.text(
                "Histórias reais de transformação através do estudo da Palavra.",
                color="#6b7280",
                text_align="center",
                size="4",
            ),
            # Grid de cards ou placeholder
            rx.cond(
                state_cls.tem_testemunhos,
                rx.hstack(
                rx.foreach(
                        state_cls.testemunhos.to(list[dict[str, str]]),
                        _testemunho_card,
                    ),
                    spacing="6",
                    flex_wrap="wrap",
                    justify="center",
                    width="100%",
                ),
                rx.text("Em breve — seja o primeiro a compartilhar!", color="#9ca3af", size="3"),
            ),
            spacing="8",
            align="center",
            max_width="1100px",
            margin="0 auto",
            padding="6rem 2rem",
        ),
        id="testemunhos",
        width="100%",
        background="#f8fafc",
    )


def _testemunho_card(t: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("❝", font_size="3rem", color="#c7d2fe", line_height="1", align_self="start"),
            rx.text(t["texto"], color="#374151", size="3", line_height="1.8", font_style="italic"),
            rx.hstack(
                rx.box(
                    rx.text(t["nome"][0], color="white", font_weight="bold", font_size="1.2rem"),
                    style={
                        "background": "linear-gradient(135deg, #4f46e5, #7c3aed)",
                        "border_radius": "50%",
                        "width": "44px",
                        "height": "44px",
                        "display": "flex",
                        "align_items": "center",
                        "justify_content": "center",
                    },
                ),
                rx.vstack(
                    rx.text(t["nome"], font_weight="bold", color="#1e1b4b", size="3"),
                    rx.text(t["local"], color="#9ca3af", size="2"),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
                align="center",
            ),
            spacing="4",
            padding="0.5rem",
        ),
        style={
            "max_width": "340px",
            "min_width": "280px",
            "transition": "transform 0.2s ease",
            "_hover": {"transform": "translateY(-4px)"},
        },
    )
