import reflex as rx
from ..states.auth import AuthState
from ..states.common import CommonState


def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon_button(
                    rx.icon("menu"),
                    on_click=CommonState.toggle_sidebar,
                    variant="ghost",
                ),
                rx.heading("Didasko", size="6", color="white"),
                spacing="2",
            ),
            rx.hstack(
                rx.badge(
                    AuthState.current_user_name,
                    variant="soft",
                    color_scheme="blue",
                ),
                rx.icon_button(
                    rx.icon("log-out"),
                    on_click=AuthState.logout,
                    variant="ghost",
                    color="white",
                ),
                spacing="3",
            ),
            justify="between",
            width="100%",
            padding_x="1rem",
        ),
        bg="var(--accent-9)",
        padding="0.75rem",
        width="100%",
        position="sticky",
        top="0",
        z_index="50",
    )
