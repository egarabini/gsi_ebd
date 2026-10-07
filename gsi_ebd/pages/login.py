import reflex as rx
from ..states.auth import AuthState


def login_page() -> rx.Component:
    """
    Página de login da plataforma GSI-EBD.
    Registro de novos usuários é feito via Landing Page → Admin aprovação.
    """
    return rx.box(
        # Fundo gradiente
        rx.center(
            rx.card(
                rx.vstack(
                    # Logo e título
                    rx.vstack(
                        rx.text("✝", font_size="3rem", color="#7c3aed", text_align="center"),
                        rx.heading("Didasko", size="7", color="#1e1b4b", text_align="center"),
                        rx.text(
                            "Estudos Bíblicos Dirigidos",
                            color="#6b7280",
                            size="3",
                            text_align="center",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.divider(),
                    # Formulário de login
                    rx.vstack(
                        rx.vstack(
                            rx.text("Email", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="seuemail@exemplo.com",
                                value=AuthState.login_email,
                                on_change=AuthState.set_login_email,
                                type="email",
                                size="3",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("Senha", size="2", font_weight="500", color="#374151"),
                            rx.input(
                                placeholder="Sua senha",
                                value=AuthState.login_password,
                                on_change=AuthState.set_login_password,
                                type="password",
                                size="3",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        # Mensagem de erro
                        rx.cond(
                            AuthState.login_error != "",
                            rx.callout(
                                AuthState.login_error,
                                icon="triangle-alert",
                                color_scheme="red",
                                variant="soft",
                                size="2",
                            ),
                        ),
                        # Botão entrar
                        rx.button(
                            "Entrar na Plataforma",
                            on_click=AuthState.login,
                            width="100%",
                            size="3",
                            style={
                                "background": "linear-gradient(135deg, #4f46e5, #7c3aed)",
                                "color": "white",
                                "font_weight": "700",
                            },
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    # Link para landing page
                    rx.center(
                        rx.vstack(
                            rx.divider(),
                            rx.text("Não tem acesso?", color="#9ca3af", size="2"),
                            rx.link(
                                rx.button(
                                    "Solicitar Participação",
                                    variant="outline",
                                    size="2",
                                    color_scheme="violet",
                                    width="100%",
                                ),
                                href="/#formulario",
                            ),
                            spacing="3",
                            align="center",
                            width="100%",
                        ),
                        width="100%",
                    ),
                    spacing="5",
                    min_width="380px",
                    padding="1rem",
                ),
                style={"box_shadow": "0 20px 60px rgba(79,70,229,0.15)"},
            ),
            height="100vh",
            style={
                "background": "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #ede9fe 100%)",
            },
        ),
    )
