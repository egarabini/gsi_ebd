"""Página de alteração de senha — obrigatória no primeiro acesso e após reset."""
import reflex as rx
from ..states.perfil import PerfilState


def alterar_senha_page() -> rx.Component:
    return rx.center(
        rx.vstack(
            # ── Logo / Título ────────────────────────────────────
            rx.vstack(
                rx.box(
                    rx.icon("key-round", size=32, color="white"),
                    bg="linear-gradient(135deg, #7c3aed, #4f46e5)",
                    border_radius="1rem",
                    padding="1rem",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.heading(
                    "Alterar Senha",
                    size="7",
                    weight="bold",
                    color="#1e1b4b",
                    text_align="center",
                ),
                rx.cond(
                    PerfilState.must_change_password,
                    rx.callout(
                        "Você precisa criar uma nova senha antes de continuar.",
                        icon="triangle-alert",
                        color_scheme="orange",
                        variant="soft",
                        size="2",
                    ),
                    rx.text(
                        "Mantenha sua conta segura atualizando sua senha regularmente.",
                        color="gray",
                        size="2",
                        text_align="center",
                    ),
                ),
                spacing="3",
                align="center",
            ),

            # ── Formulário ───────────────────────────────────────
            rx.card(
                rx.vstack(
                    # Senha atual
                    rx.vstack(
                        rx.text("Senha atual", size="2", weight="medium", color="#374151"),
                        rx.input(
                            placeholder="Digite sua senha atual",
                            type="password",
                            value=PerfilState.senha_atual,
                            on_change=PerfilState.set_senha_atual,
                            size="3",
                            width="100%",
                            id="senha-atual",
                        ),
                        spacing="1",
                        width="100%",
                    ),

                    rx.divider(margin_y="0.5rem"),

                    # Nova senha
                    rx.vstack(
                        rx.text("Nova senha", size="2", weight="medium", color="#374151"),
                        rx.input(
                            placeholder="Mínimo 8 caracteres",
                            type="password",
                            value=PerfilState.nova_senha,
                            on_change=PerfilState.set_nova_senha,
                            size="3",
                            width="100%",
                            id="nova-senha",
                            color_scheme=rx.cond(PerfilState.senha_fraca, "red", "violet"),
                        ),
                        # Indicador de força
                        rx.cond(
                            PerfilState.senha_fraca,
                            rx.hstack(
                                rx.icon("octagon-x", size=14, color="#ef4444"),
                                rx.text(
                                    "Mínimo 8 caracteres",
                                    size="1",
                                    color="#ef4444",
                                ),
                                spacing="1",
                                align="center",
                            ),
                        ),
                        spacing="1",
                        width="100%",
                    ),

                    # Confirmar nova senha
                    rx.vstack(
                        rx.text("Confirmar nova senha", size="2", weight="medium", color="#374151"),
                        rx.input(
                            placeholder="Repita a nova senha",
                            type="password",
                            value=PerfilState.confirma_senha,
                            on_change=PerfilState.set_confirma_senha,
                            size="3",
                            width="100%",
                            id="confirma-senha",
                            color_scheme=rx.cond(PerfilState.senhas_divergem, "red", "violet"),
                        ),
                        rx.cond(
                            PerfilState.senhas_divergem,
                            rx.hstack(
                                rx.icon("octagon-x", size=14, color="#ef4444"),
                                rx.text(
                                    "As senhas não coincidem",
                                    size="1",
                                    color="#ef4444",
                                ),
                                spacing="1",
                                align="center",
                            ),
                        ),
                        spacing="1",
                        width="100%",
                    ),

                    # Dicas de segurança
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("shield-check", size=14, color="#6b7280"),
                                rx.text("Use ao menos 8 caracteres", size="1", color="#6b7280"),
                                spacing="1", align="center",
                            ),
                            rx.hstack(
                                rx.icon("shield-check", size=14, color="#6b7280"),
                                rx.text("Combine letras, números e símbolos", size="1", color="#6b7280"),
                                spacing="1", align="center",
                            ),
                            rx.hstack(
                                rx.icon("shield-check", size=14, color="#6b7280"),
                                rx.text("Não reutilize a senha atual", size="1", color="#6b7280"),
                                spacing="1", align="center",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        bg="#f9fafb",
                        border_radius="0.5rem",
                        padding="0.75rem",
                        width="100%",
                    ),

                    # Mensagem de erro
                    rx.cond(
                        PerfilState.perfil_error != "",
                        rx.callout(
                            PerfilState.perfil_error,
                            icon="octagon-alert",
                            color_scheme="red",
                            variant="soft",
                            size="2",
                        ),
                    ),

                    # Botão de salvar
                    rx.button(
                        rx.cond(
                            PerfilState.is_loading,
                            rx.hstack(
                                rx.spinner(size="2"),
                                rx.text("Salvando..."),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                rx.icon("save", size=16),
                                rx.text("Salvar nova senha"),
                                spacing="2",
                                align="center",
                            ),
                        ),
                        on_click=PerfilState.alterar_senha,
                        color_scheme="violet",
                        size="3",
                        width="100%",
                        disabled=~PerfilState.pode_salvar,
                    ),

                    # Link para voltar (apenas se não for troca obrigatória)
                    rx.cond(
                        ~PerfilState.must_change_password,
                        rx.center(
                            rx.link(
                                rx.hstack(
                                    rx.icon("arrow-left", size=14),
                                    rx.text("Voltar ao painel", size="2"),
                                    spacing="1",
                                    align="center",
                                ),
                                href=PerfilState.redirect_path,
                                color="#7c3aed",
                            ),
                        ),
                    ),

                    spacing="4",
                    width="100%",
                ),
                padding="2rem",
                width="100%",
                box_shadow="0 8px 32px rgba(0,0,0,0.1)",
                border_radius="1.25rem",
            ),

            width="100%",
            max_width="28rem",
            spacing="5",
        ),
        min_height="100vh",
        bg="linear-gradient(135deg, #f5f3ff 0%, #ede9fe 50%, #ddd6fe 100%)",
        padding="2rem",
    )
