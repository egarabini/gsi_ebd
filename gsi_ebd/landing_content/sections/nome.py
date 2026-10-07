"""Seção 'Por que Didasko?' — a origem e o significado do nome."""
import reflex as rx

COR = "#7c3aed"


def _bloco(icone: str, titulo: str, texto: str, citacao: str = "") -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icone, size=22, color=COR),
                rx.text(titulo, size="4", weight="bold", color="#1e1b4b"),
                spacing="2",
                align="center",
            ),
            rx.text(texto, size="3", color="gray", line_height="1.7"),
            rx.cond(
                citacao != "",
                rx.callout(citacao, icon="quote", variant="surface", color_scheme="violet"),
            ),
            spacing="3",
            align="start",
        ),
        width="100%",
        padding="1.5rem",
    )


def nome_section(titulo: str = "Por que Didasko?", texto: str = "") -> rx.Component:
    """Explica o nome: do verbo grego ao Didaskaleion de Alexandria.

    NOTA: nao repetimos o cabecalho "Sobre" aqui. O `titulo` que chega e o valor
    de `sobre_titulo` do SiteConfig, que ja aparece na secao Sobre logo acima —
    repetir criava DOIS titulos iguais na mesma pagina (visivel no site).
    """
    return rx.vstack(
        rx.cond(
            texto != "",
            rx.text(texto, size="3", color="gray", text_align="center",
                    max_width="820px", line_height="1.8", white_space="pre-line"),
        ),
        rx.grid(
            _bloco(
                "book-open",
                "διδάσκω — didasko",
                "Verbo grego que significa ENSINAR. É a palavra que Jesus usa na "
                "Grande Comissão: «fazei discípulos... ensinando-os a guardar todas "
                "as coisas que vos tenho ordenado».",
                "Mt 28.19-20",
            ),
            _bloco(
                "landmark",
                "Didaskaleion — lugar de ensino",
                "Era o nome oficial da Escola de Alexandria, o grande centro de "
                "formação cristã dos primeiros séculos — onde a fé era pensada com "
                "rigor, piedade e coragem intelectual.",
                "Alexandria, séculos II–IV",
            ),
            _bloco(
                "users",
                "O que fazemos com esse nome",
                "Um lugar de ensino sério da Palavra, acessível a todo cristão, no "
                "seu ritmo — com acompanhamento humano de verdade em cada passo.",
            ),
            columns=rx.breakpoints(initial="1", md="3"),
            spacing="4",
            width="100%",
        ),
        spacing="6",
        padding="4rem 1.5rem",
        width="100%",
        background="linear-gradient(180deg, #ffffff 0%, #faf8ff 100%)",
        align="center",
    )
