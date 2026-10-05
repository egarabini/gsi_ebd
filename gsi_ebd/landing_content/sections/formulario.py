"""Seção Formulário de Interesse — captura leads via landing page."""
import reflex as rx


def formulario_section(
    state_class,
    descricao: str = "Preencha o formulário abaixo e nossa equipe entrará em contato para apresentar a plataforma e as próximas turmas.",
) -> rx.Component:
    """
    state_class: o State do Reflex que gerencia o formulário (LandingState).
    """
    return rx.box(
        rx.vstack(
            rx.badge("Participe", color_scheme="violet", variant="solid", size="2"),
            rx.heading(
                "Demonstre seu Interesse",
                size="7",
                color="white",
                text_align="center",
            ),
            rx.text(
                descricao,
                color="rgba(255,255,255,0.8)",
                text_align="center",
                size="4",
                max_width="600px",
                line_height="1.7",
            ),
            # Card do formulário
            rx.card(
                rx.vstack(
                    rx.grid(
                        rx.vstack(
                            rx.text("Nome Completo *", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="Seu nome completo",
                                value=state_class.form_nome,
                                on_change=state_class.set_form_nome,
                                size="3",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Email *", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="seuemail@exemplo.com",
                                value=state_class.form_email,
                                on_change=state_class.set_form_email,
                                type="email",
                                size="3",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Telefone / WhatsApp", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="(00) 00000-0000",
                                value=state_class.form_telefone,
                                on_change=state_class.set_form_telefone,
                                size="3",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Cidade / Estado", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="Ex: São Paulo / SP",
                                value=state_class.form_cidade_estado,
                                on_change=state_class.set_form_cidade_estado,
                                size="3",
                            ),
                            spacing="1",
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text("Membro de Igreja?", size="2", font_weight="500", color="#374151"),
                        rx.hstack(
                            rx.checkbox(
                                "Sim, sou membro de uma igreja",
                                checked=state_class.form_membro_igreja,
                                on_change=state_class.set_form_membro_igreja,
                            ),
                            spacing="2",
                        ),
                        rx.cond(
                            state_class.form_membro_igreja,
                            rx.input(
                                placeholder="Nome da sua Igreja / Denominação",
                                value=state_class.form_nome_igreja,
                                on_change=state_class.set_form_nome_igreja,
                                size="3",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    rx.vstack(
                        rx.text("Mensagem (opcional)", size="2", font_weight="500", color="#374151"),
                        rx.text_area(
                            placeholder="Conte um pouco sobre você e por que tem interesse na plataforma...",
                            value=state_class.form_mensagem,
                            on_change=state_class.set_form_mensagem,
                            rows="4",
                            size="3",
                        ),
                        spacing="1",
                        width="100%",
                    ),
                    # Feedback
                    rx.cond(
                        state_class.form_error != "",
                        rx.callout(
                        state_class.form_error,
                        icon="triangle-alert",
                        color_scheme="red",
                        variant="soft",
                    ),    ),
                    rx.cond(
                        state_class.form_success,
                        rx.callout(
                        "✅ Formulário enviado! Nossa equipe entrará em contato em breve.",
                        icon="check",
                        color_scheme="green",
                        variant="soft",
                    ),    ),
                    # Botão enviar
                    rx.button(
                        rx.cond(
                            state_class.form_loading,
                            rx.spinner(size="3"),
                            rx.hstack(
                                rx.icon("send-horizontal", size=18),
                                rx.text("Enviar Interesse"),
                                spacing="2",
                            ),
                        ),
                        on_click=state_class.submit_form,
                        disabled=state_class.form_success,
                        size="3",
                        width="100%",
                        style={
                            "background": "linear-gradient(135deg, #4f46e5, #7c3aed)",
                            "color": "white",
                            "font_weight": "700",
                            "_hover": {"opacity": "0.9"},
                        },
                    ),
                    spacing="5",
                    width="100%",
                ),
                style={"max_width": "700px", "width": "100%"},
            ),
            spacing="8",
            align="center",
            max_width="900px",
            margin="0 auto",
            padding="6rem 2rem",
        ),
        id="formulario",
        width="100%",
        style={
            "background": "linear-gradient(135deg, #1e1b4b, #4f46e5)",
        },
    )
