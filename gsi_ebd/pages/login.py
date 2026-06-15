import reflex as rx
from ..states.auth import AuthState


def login_page() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("GSI-EBD", size="8", text_align="center", color="var(--accent-9)"),
                rx.text("Estudos Biblicos Dirigidos", text_align="center", color="gray"),
                rx.divider(margin_y="0.5rem"),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Entrar", value="login"),
                        rx.tabs.trigger("Criar Conta", value="register"),
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.input(
                                placeholder="Email",
                                value=AuthState.login_email,
                                on_change=AuthState.set_login_email,
                                type="email",
                                size="lg",
                            ),
                            rx.input(
                                placeholder="Senha",
                                value=AuthState.login_password,
                                on_change=AuthState.set_login_password,
                                type="password",
                                size="lg",
                            ),
                            rx.cond(
                                AuthState.login_error != "",
                                rx.text(AuthState.login_error, color="red", font_size="sm"),
                            ),
                            rx.button(
                                "Entrar",
                                on_click=AuthState.login,
                                width="100%",
                                size="lg",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        value="login",
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.input(
                                placeholder="Nome",
                                value=AuthState.register_nome,
                                on_change=AuthState.set_register_nome,
                                size="lg",
                            ),
                            rx.input(
                                placeholder="Email",
                                value=AuthState.register_email,
                                on_change=AuthState.set_register_email,
                                type="email",
                                size="lg",
                            ),
                            rx.input(
                                placeholder="Senha",
                                value=AuthState.register_password,
                                on_change=AuthState.set_register_password,
                                type="password",
                                size="lg",
                            ),
                            rx.cond(
                                AuthState.register_error != "",
                                rx.text(AuthState.register_error, color="red", font_size="sm"),
                            ),
                            rx.button(
                                "Criar Conta",
                                on_click=AuthState.register,
                                width="100%",
                                size="lg",
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        value="register",
                    ),
                    default_value="login",
                    width="100%",
                ),
                spacing="3",
                min_width="350px",
            ),
            size="3",
        ),
        height="100vh",
        bg="var(--accent-1)",
    )
