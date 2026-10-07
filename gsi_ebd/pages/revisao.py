"""Fila de correcao do instrutor — o ciclo humano do estudo acompanhado."""
import reflex as rx

from ..components.navbar import navbar
from ..components.sidebar import sidebar
from ..states.revisao import RevisaoState


def _item_pendente(item: dict) -> rx.Component:
    aberto = RevisaoState.resposta_aberta_id == item["response_id"]
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(item["aluno_nome"], color_scheme="violet", variant="soft"),
                rx.text(item["estudo_titulo"], size="2", color="gray"),
                rx.spacer(),
                rx.text(item["quando"], size="1", color="gray"),
                width="100%",
                align="center",
            ),
            rx.text("Resposta do aluno:", size="1", weight="bold", color="gray"),
            rx.callout(item["resposta"], icon="message-square", variant="surface"),
            rx.cond(
                aberto,
                rx.vstack(
                    # ── Apoio da IA: parecer PRELIMINAR ────────────────────────
                    # A IA nunca fala com o aluno: ela sugere, o instrutor decide.
                    rx.hstack(
                        rx.button(
                            rx.icon("sparkles", size=15),
                            rx.cond(RevisaoState.sugerindo,
                                    "Consultando...", "Sugerir com IA"),
                            on_click=RevisaoState.pedir_sugestao,
                            disabled=RevisaoState.sugerindo,
                            variant="soft", color_scheme="violet", size="2",
                        ),
                        rx.cond(
                            RevisaoState.sugestao_erro != "",
                            rx.text(RevisaoState.sugestao_erro, size="1", color="orange"),
                        ),
                        spacing="2", align="center",
                    ),
                    rx.cond(
                        RevisaoState.sugestao_disponivel,
                        rx.card(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("sparkles", size=16, color="#7c3aed"),
                                    rx.text("Sugestão preliminar da IA", size="2",
                                            weight="bold", color="#1e1b4b"),
                                    rx.badge(RevisaoState.sugestao_aderencia,
                                             color_scheme="violet", variant="soft", size="1"),
                                    spacing="2", align="center",
                                ),
                                rx.cond(
                                    RevisaoState.sugestao_comentario != "",
                                    rx.text(RevisaoState.sugestao_comentario, size="2",
                                            color="gray"),
                                ),
                                rx.cond(
                                    RevisaoState.sugestao_sugestao != "",
                                    rx.callout(RevisaoState.sugestao_sugestao,
                                               icon="lightbulb", variant="surface",
                                               color_scheme="violet"),
                                ),
                                rx.hstack(
                                    rx.button("Usar sugestão", on_click=RevisaoState.usar_sugestao,
                                              variant="soft", color_scheme="violet", size="1"),
                                    rx.button("Descartar", on_click=RevisaoState.descartar_sugestao,
                                              variant="ghost", size="1"),
                                    spacing="2",
                                ),
                                rx.text(
                                    "Revise antes de enviar — o parecer é seu, não da IA.",
                                    size="1", color="gray", font_style="italic",
                                ),
                                spacing="2", width="100%",
                            ),
                            width="100%",
                            background="#faf8ff",
                        ),
                    ),
                    rx.text_area(
                        placeholder="Escreva seu parecer para o aluno...",
                        value=RevisaoState.parecer_texto,
                        on_change=RevisaoState.set_parecer_texto,
                        rows="3",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.text("Considerar:", size="2"),
                        rx.switch(
                            checked=RevisaoState.considerou_correto,
                            on_change=RevisaoState.set_considerou_correto,
                        ),
                        rx.text(
                            rx.cond(RevisaoState.considerou_correto,
                                    "Resposta correta", "Precisa revisar"),
                            size="2", color="gray",
                        ),
                        spacing="2", align="center",
                    ),
                    rx.hstack(
                        rx.button("Enviar parecer", on_click=RevisaoState.salvar_parecer,
                                  color_scheme="green", size="2"),
                        rx.button("Cancelar", on_click=RevisaoState.fechar_resposta,
                                  variant="soft", size="2"),
                        spacing="2",
                    ),
                    spacing="2", width="100%",
                ),
                rx.button("Avaliar esta resposta",
                          on_click=RevisaoState.abrir_resposta(item["response_id"]),
                          variant="soft", color_scheme="violet", size="2"),
            ),
            spacing="2", width="100%",
        ),
        width="100%",
    )


def revisao_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Correcao de Respostas", size="7", weight="bold",
                                   color="#1e1b4b"),
                        rx.text("Avalie as respostas abertas dos seus alunos e devolva um parecer.",
                                color="gray", size="2"),
                        spacing="0", align="start",
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("refresh-cw", size=16), "Atualizar",
                              on_click=RevisaoState.load_fila, variant="soft",
                              color_scheme="violet", size="2"),
                    align="center", width="100%",
                ),
                rx.badge(RevisaoState.fila_label, color_scheme="orange", variant="soft", size="2"),
                rx.cond(
                    RevisaoState.mensagem != "",
                    rx.callout(
                        RevisaoState.mensagem,
                        icon="info",
                        color_scheme=rx.cond(RevisaoState.mensagem_tipo == "success",
                                             "green", "red"),
                        variant="soft",
                    ),
                ),
                rx.cond(
                    RevisaoState.tem_pendentes,
                    rx.vstack(
                        rx.foreach(RevisaoState.pendentes, _item_pendente),
                        spacing="3", width="100%",
                    ),
                    rx.card(
                        rx.vstack(
                            rx.icon("circle-check", size=40, color="green"),
                            rx.heading("Tudo em dia!", size="4"),
                            rx.text("Nenhuma resposta aguardando sua correcao no momento.",
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
