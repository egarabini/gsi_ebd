"""Seção Níveis de Estudo."""
import reflex as rx


_NIVEIS = [
    {
        "nivel": "Básico",
        "icone": "📖",
        "cor": "#10b981",
        "descricao": "Fundamentos da fé — ideal para quem está iniciando a jornada bíblica.",
        "topicos": ["Plano da Salvação", "A Bíblia", "Oração e Devoção"],
        "chave": "niveis_basico_desc",
    },
    {
        "nivel": "Médio",
        "icone": "🔍",
        "cor": "#3b82f6",
        "descricao": "Aprofundamento doutrinário — para quem já domina os fundamentos.",
        "topicos": ["Doutrinas Cristãs", "História da Igreja", "Ética Bíblica"],
        "chave": "niveis_medio_desc",
    },
    {
        "nivel": "Avançado",
        "icone": "🏛️",
        "cor": "#8b5cf6",
        "descricao": "Hermenêutica e teologia — para estudo avançado e contextualização.",
        "topicos": ["Hermenêutica", "Teologia Bíblica", "Línguas Originais"],
        "chave": "niveis_avancado_desc",
    },
    {
        "nivel": "Master",
        "icone": "⭐",
        "cor": "#f59e0b",
        "descricao": "Especialização e liderança — para formação de líderes e gestores de fé.",
        "topicos": ["Teologia Sistemática", "Liderança Ministerial", "Mentoria"],
        "chave": "niveis_master_desc",
    },
]


def niveis_section(descricoes: dict = {}) -> rx.Component:
    """
    descricoes: dict {chave_config: texto} — passado pelo controller
                para permitir textos dinâmicos do banco.
    """
    return rx.box(
        rx.vstack(
            rx.badge("Trilha de Aprendizado", color_scheme="violet", variant="soft", size="2"),
            rx.heading("Níveis de Estudo", size="7", color="#1e1b4b", text_align="center"),
            rx.text(
                "Uma jornada progressiva de crescimento espiritual — do fundamento ao masterado.",
                color="#6b7280",
                text_align="center",
                size="4",
                max_width="600px",
            ),
            # Linha de progressão
            rx.hstack(
                *[_nivel_card(n, descricoes.get(n["chave"], n["descricao"])) for n in _NIVEIS],
                spacing="4",
                flex_wrap="wrap",
                justify="center",
                width="100%",
            ),
            spacing="8",
            align="center",
            max_width="1200px",
            margin="0 auto",
            padding="6rem 2rem",
        ),
        id="niveis",
        width="100%",
        background="white",
    )


def _nivel_card(nivel: dict, descricao: str) -> rx.Component:
    cor = nivel["cor"]
    return rx.card(
        rx.vstack(
            # Badge de ordem
            rx.box(
                rx.text(nivel["icone"], font_size="2rem"),
                style={
                    "background": f"{cor}15",
                    "border_radius": "50%",
                    "padding": "1rem",
                    "width": "72px",
                    "height": "72px",
                    "display": "flex",
                    "align_items": "center",
                    "justify_content": "center",
                },
            ),
            rx.badge(nivel["nivel"], style={"background": cor, "color": "white"}, size="2"),
            rx.text(descricao, color="#6b7280", size="2", text_align="center", line_height="1.6"),
            rx.vstack(
                *[
                    rx.hstack(
                        rx.icon("check", size=14, color=cor),
                        rx.text(t, size="2", color="#374151"),
                        spacing="2",
                    )
                    for t in nivel["topicos"]
                ],
                spacing="2",
                align="start",
                width="100%",
            ),
            spacing="4",
            align="center",
            padding="1.5rem",
        ),
        style={
            "max_width": "250px",
            "min_width": "220px",
            "border_top": f"4px solid {cor}",
            "transition": "all 0.25s ease",
            "_hover": {
                "transform": "translateY(-6px)",
                "box_shadow": f"0 12px 32px {cor}30",
            },
        },
    )
