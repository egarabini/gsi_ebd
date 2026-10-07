"""Pareceres do instrutor sobre as respostas do aluno."""
import reflex as rx

from ..components.navbar import navbar
from ..components.sidebar import sidebar
from ..states.aluno import AlunoState


def _parecer(item: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(item["estudo_titulo"], color_scheme="violet", variant="soft"),
                rx.badge(item["correto"],
                         color_scheme=rx.cond(item["correto"] == "sim", "green", "orange"),
                         variant="soft"),
                rx.spacer(),
                rx.text(item["quando"], size="1", color="gray"),
                width="100%", align="center",
            ),
            rx.text("Sua resposta:", size="1", weight="bold", color="gray"),
            rx.callout(item["resposta"], icon="message-square", variant="surface"),
            rx.text("Parecer do instrutor:", size="1", weight="bold", color="gray"),
            rx.callout(item["parecer"], icon="user-check", color_scheme="green",
                       variant="surface"),
            rx.text("— ", item["instrutor"], size="1", color="gray"),
            spacing="2", width="100%",
        ),
        width="100%",
    )


def pareceres_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Meus Pareceres", size="7", weight="bold", color="#1e1b4b"),
                        rx.text("O retorno do seu instrutor sobre as respostas que voce escreveu.",
                                color="gray", size="2"),
                        spacing="0", align="start",
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("arrow-left", size=16), "Voltar aos estudos",
                              on_click=rx.redirect("/aluno"), variant="soft", size="2"),
                    align="center", width="100%",
                ),
                rx.cond(
                    AlunoState.tem_pareceres,
                    rx.vstack(rx.foreach(AlunoState.pareceres, _parecer),
                              spacing="3", width="100%"),
                    rx.card(
                        rx.vstack(
                            rx.icon("inbox", size=40, color="gray"),
                            rx.heading("Nenhum parecer ainda", size="4"),
                            rx.text("Quando seu instrutor avaliar suas respostas, elas aparecerao aqui.",
                                    color="gray", size="2"),
                            spacing="2", align="center",
                        ),
                        width="100%", padding="3rem",
                    ),
                ),
                spacing="4", padding="2rem", width="100%",
                height="calc(100vh - 52px)", overflow_y="auto",
            ),
            spacing="0", width="100%",
        ),
        spacing="0", width="100%", height="100vh",
    )
