"""Página de Homenagens do Didasko.

Honra quem nos ensinou a ensinar. Os registros ficam no SiteConfig (chave
`homenagens`), como lista de blocos separados por linha, no formato:

    Título :: Descrição :: Referência

Assim o Admin edita a homenagem pelo painel, sem tocar em código.
"""
from typing import List

import reflex as rx
from sqlmodel import select

from ..models.site_content import SiteConfig


class HomenagensState(rx.State):
    homenagens: List[dict] = []
    titulo: str = "Homenagens"
    intro: str = ""

    def load(self):
        with rx.session() as session:
            cfg = {c.chave: c.valor for c in session.exec(select(SiteConfig)).all()}
        self.titulo = cfg.get("homenagens_titulo", "Homenagens")
        self.intro = cfg.get(
            "homenagens_intro",
            "Nenhum ensino nasce do nada. Esta página honra quem nos ensinou a ensinar.",
        )
        itens = []
        for i, linha in enumerate(cfg.get("homenagens", "").splitlines()):
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            partes = [p.strip() for p in linha.split("::")]
            if not partes or not partes[0]:
                continue
            itens.append({
                "id": str(i),
                "titulo": partes[0],
                "descricao": partes[1] if len(partes) > 1 else "",
                "referencia": partes[2] if len(partes) > 2 else "",
            })
        self.homenagens = itens


def _card(h: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("award", size=22, color="#7c3aed"),
                rx.text(h["titulo"], size="4", weight="bold", color="#1e1b4b"),
                spacing="2",
                align="center",
            ),
            rx.cond(
                h["descricao"] != "",
                rx.text(h["descricao"], size="3", color="gray", line_height="1.7"),
            ),
            rx.cond(
                h["referencia"] != "",
                rx.text("— ", h["referencia"], size="2", color="#7c3aed", weight="medium"),
            ),
            spacing="3",
            align="start",
        ),
        width="100%",
        padding="1.5rem",
    )


def homenagens_page() -> rx.Component:
    from ..components.navbar import navbar
    from ..components.sidebar import sidebar

    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.vstack(
                    rx.heading(HomenagensState.titulo, size="8", weight="bold",
                               color="#1e1b4b", text_align="center"),
                    rx.cond(
                        HomenagensState.intro != "",
                        rx.text(HomenagensState.intro, size="3", color="gray",
                                text_align="center", max_width="760px"),
                    ),
                    rx.link(
                        rx.button(rx.icon("arrow-left", size=16), "Voltar ao início",
                                  variant="soft", color_scheme="violet", size="2"),
                        href="/",
                    ),
                    spacing="4", align="center", width="100%", padding="3rem 0 1rem 0",
                ),
                rx.cond(
                    HomenagensState.homenagens.length() > 0,
                    rx.vstack(
                        rx.foreach(HomenagensState.homenagens, _card),
                        spacing="4", width="100%", max_width="820px",
                    ),
                    rx.callout(
                        "As homenagens ainda serão publicadas.",
                        icon="info", variant="surface", color_scheme="gray",
                    ),
                ),
                spacing="6",
                padding="1rem 2rem 4rem 2rem",
                width="100%",
                align="center",
                height="calc(100vh - 52px)",
                overflow_y="auto",
            ),
            spacing="0",
            width="100%",
        ),
        spacing="0",
        width="100%",
        min_height="100vh",
    )
