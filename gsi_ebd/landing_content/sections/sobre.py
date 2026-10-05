"""Seção Sobre — apresenta a plataforma."""
import reflex as rx


def sobre_section(
    titulo: str = "Sobre a Plataforma GSI-EBD",
    texto: str = "O GSI-EBD é uma plataforma criada para facilitar o crescimento espiritual de forma estruturada, guiada e progressiva.",
    missao: str = "Conectar pessoas à Palavra de Deus por meio de estudos estruturados e acompanhamento personalizado.",
    visao: str = "Ser a referência em estudos bíblicos digitais no Brasil, formando discípulos comprometidos com a Escritura.",
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.badge("Nossa História", color_scheme="violet", variant="soft", size="2"),
            rx.heading(titulo, size="7", color="#1e1b4b", text_align="center"),
            rx.text(
                texto,
                color="#6b7280",
                text_align="center",
                size="4",
                max_width="700px",
                line_height="1.8",
            ),
            # Cards missão / visão
            rx.hstack(
                _card_info("🎯", "Missão", missao, "#4f46e5"),
                _card_info("👁️", "Visão", visao, "#7c3aed"),
                spacing="6",
                flex_wrap="wrap",
                justify="center",
                width="100%",
            ),
            spacing="8",
            align="center",
            max_width="1000px",
            margin="0 auto",
            padding="6rem 2rem",
        ),
        id="sobre",
        width="100%",
        background="#f8fafc",
    )


def _card_info(icone: str, titulo: str, texto: str, cor: str) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(icone, font_size="2.5rem"),
            rx.heading(titulo, size="5", color=cor),
            rx.text(texto, color="#6b7280", size="3", line_height="1.7", text_align="center"),
            spacing="3",
            align="center",
            padding="1rem",
        ),
        style={
            "max_width": "380px",
            "border_top": f"4px solid {cor}",
            "transition": "transform 0.2s ease",
            "_hover": {"transform": "translateY(-4px)"},
        },
    )
