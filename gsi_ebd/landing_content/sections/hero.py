"""
Seção Hero — topo da landing page.
Conteúdo dinâmico via SiteConfig (chaves: hero_titulo, hero_subtitulo, hero_cta_texto).
"""
import reflex as rx
from sqlmodel import select

from ...models.site_content import SiteConfig


def _get_config(session, chave: str, default: str = "") -> str:
    cfg = session.exec(select(SiteConfig).where(SiteConfig.chave == chave)).first()
    return cfg.valor if cfg else default


def hero_section(
    titulo: str = "Cresça na Palavra — A qualquer hora, em qualquer lugar",
    subtitulo: str = "Uma plataforma de estudos bíblicos dirigidos, com acompanhamento personalizado para cada etapa da sua jornada de fé.",
    cta_texto: str = "Quero Participar",
) -> rx.Component:
    """
    Seção Hero com gradiente, texto dinâmico e CTA.
    Os parâmetros são valores default; a página lê do banco via SiteConfig.
    """
    return rx.box(
        # Fundo com gradiente profundo
        rx.box(
            rx.vstack(
                # Ícone / Logo decorativo
                rx.text("✝", font_size="4rem", color="rgba(255,255,255,0.3)"),
                # Badge superior
                rx.badge(
                    "Plataforma de Estudos Bíblicos Dirigidos",
                    color_scheme="violet",
                    variant="soft",
                    size="2",
                    style={"backdrop_filter": "blur(8px)"},
                ),
                # Título principal
                rx.heading(
                    titulo,
                    size="9",
                    color="white",
                    text_align="center",
                    max_width="800px",
                    style={
                        "text_shadow": "0 2px 32px rgba(0,0,0,0.3)",
                        "line_height": "1.15",
                    },
                ),
                # Subtítulo
                rx.text(
                    subtitulo,
                    color="rgba(255,255,255,0.85)",
                    text_align="center",
                    size="4",
                    max_width="600px",
                    line_height="1.7",
                ),
                # Botões CTA
                rx.hstack(
                    rx.link(
                        rx.button(
                            cta_texto,
                            rx.icon("arrow-right", size=18),
                            size="4",
                            variant="solid",
                            color_scheme="violet",
                            style={
                                "background": "white",
                                "color": "#4f46e5",
                                "font_weight": "700",
                                "padding": "0 2rem",
                                "_hover": {
                                    "transform": "translateY(-2px)",
                                    "box_shadow": "0 8px 24px rgba(0,0,0,0.2)",
                                },
                                "transition": "all 0.2s ease",
                            },
                        ),
                        href="#formulario",
                    ),
                    rx.link(
                        rx.button(
                            "Saber Mais",
                            rx.icon("chevron-down", size=18),
                            size="4",
                            variant="outline",
                            style={
                                "border_color": "rgba(255,255,255,0.5)",
                                "color": "white",
                                "_hover": {
                                    "background": "rgba(255,255,255,0.1)",
                                    "border_color": "white",
                                },
                                "transition": "all 0.2s ease",
                            },
                        ),
                        href="#sobre",
                    ),
                    spacing="4",
                    flex_wrap="wrap",
                    justify="center",
                ),
                # Stats rápidos
                rx.hstack(
                    _stat_item("4", "Níveis de Estudo"),
                    _stat_divider(),
                    _stat_item("100%", "Online"),
                    _stat_divider(),
                    _stat_item("✝", "Fidelidade Bíblica"),
                    spacing="6",
                    flex_wrap="wrap",
                    justify="center",
                    padding_top="2rem",
                    style={"border_top": "1px solid rgba(255,255,255,0.15)"},
                ),
                spacing="6",
                align="center",
                padding="6rem 2rem",
                max_width="1000px",
                margin="0 auto",
            ),
            style={
                "background": "linear-gradient(135deg, #1e1b4b 0%, #4f46e5 50%, #7c3aed 100%)",
                "min_height": "100vh",
                "display": "flex",
                "align_items": "center",
                "position": "relative",
                "overflow": "hidden",
            },
        ),
        id="hero",
        width="100%",
    )


def _stat_item(valor: str, label: str) -> rx.Component:
    return rx.vstack(
        rx.text(valor, font_size="2rem", font_weight="800", color="white"),
        rx.text(label, color="rgba(255,255,255,0.7)", size="2"),
        spacing="1",
        align="center",
    )


def _stat_divider() -> rx.Component:
    return rx.box(
        width="1px",
        height="40px",
        background="rgba(255,255,255,0.2)",
    )
