"""Rodapé da landing page."""
import reflex as rx


def rodape_section(
    email: str = "contato@gsi-ebd.com.br",
    telefone: str = "(00) 00000-0000",
    instagram: str = "",
    youtube: str = "",
    whatsapp: str = "",
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                # Logo / Nome
                rx.vstack(
                    rx.hstack(
                        rx.text("✝", font_size="1.8rem", color="#c7d2fe"),
                        rx.heading("Didasko", size="5", color="white"),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        "Estudos Bíblicos Dirigidos",
                        color="#94a3b8",
                        size="2",
                    ),
                    spacing="2",
                    align="start",
                ),
                rx.spacer(),
                # Links de contato
                rx.vstack(
                    rx.text("Contato", color="white", font_weight="bold", size="3"),
                    rx.hstack(
                        rx.icon("mail", size=14, color="#94a3b8"),
                        rx.text(email, color="#94a3b8", size="2"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.icon("phone", size=14, color="#94a3b8"),
                        rx.text(telefone, color="#94a3b8", size="2"),
                        spacing="2",
                    ),
                    spacing="2",
                    align="start",
                ),
                rx.spacer(),
                # Redes sociais
                rx.vstack(
                    rx.text("Redes Sociais", color="white", font_weight="bold", size="3"),
                    rx.hstack(
                        rx.cond(
                            instagram != "",
                            rx.link(
                                rx.icon("globe", size=20, color="#94a3b8"),
                                href=instagram,
                                is_external=True,
                            ),
                        ),
                        rx.cond(
                            youtube != "",
                            rx.link(
                                rx.icon("monitor", size=20, color="#94a3b8"),
                                href=youtube,
                                is_external=True,
                            ),
                        ),
                        rx.cond(
                            whatsapp != "",
                            rx.link(
                                rx.icon("message-square", size=20, color="#94a3b8"),
                                href=f"https://wa.me/{whatsapp}",
                                is_external=True,
                            ),
                        ),
                        spacing="4",
                    ),
                    spacing="2",
                    align="start",
                ),
                flex_wrap="wrap",
                width="100%",
                spacing="8",
                align="start",
            ),
            rx.divider(opacity="0.2"),
            rx.hstack(
                rx.text(
                    "© 2026 Didasko — Todos os direitos reservados.",
                    color="#64748b",
                    size="2",
                ),
                rx.spacer(),
                rx.link(
                    rx.button(
                        rx.icon("lock", size=14),
                        rx.text("Área Restrita"),
                        size="1",
                        variant="ghost",
                        color_scheme="gray",
                    ),
                    href="/login",
                ),
                width="100%",
                flex_wrap="wrap",
            ),
            spacing="6",
            max_width="1100px",
            margin="0 auto",
            padding="3rem 2rem",
        ),
        width="100%",
        style={"background": "#0f172a"},
    )
