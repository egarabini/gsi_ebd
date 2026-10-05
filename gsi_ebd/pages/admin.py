"""Página do Administrador — Gestores, Coordenadores, Leads, Estudos."""
import reflex as rx
from ..states.admin import AdminState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


def admin_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.heading("Painel do Administrador", size="7", color="#1e1b4b"),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Gestores", value="gestores"),
                        rx.tabs.trigger("Coordenadores", value="coordenadores"),
                        rx.tabs.trigger("Aprovação de Estudos", value="estudos"),
                        rx.tabs.trigger("Leads", value="leads"),
                    ),
                    rx.tabs.content(_gestores_tab(), value="gestores"),
                    rx.tabs.content(_coordenadores_tab(), value="coordenadores"),
                    rx.tabs.content(_estudos_tab(), value="estudos"),
                    rx.tabs.content(_leads_tab(), value="leads"),
                    default_value="gestores",
                    width="100%",
                ),
                spacing="4",
                padding="2rem",
                width="100%",
                overflow_y="auto",
                height="calc(100vh - 52px)",
            ),
            spacing="0",
            width="100%",
        ),
        spacing="0",
        width="100%",
        height="100vh",
        on_mount=AdminState.load_gestores,
    )


# ── Cards ─────────────────────────────────────────────────────────────────────

def _user_card(u: dict) -> rx.Component:
    """Card genérico para usuários (Gestor ou Coordenador)."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(u["nome"], font_weight="bold", size="3"),
                rx.text(u["email"], color="gray", size="2"),
                spacing="0",
            ),
            rx.spacer(),
            rx.badge(
                u["status"],
                color_scheme=rx.cond(u["status"] == "ativo", "green", "orange"),
                variant="soft",
            ),
            rx.hstack(
                rx.button(
                    "Ativar",
                    on_click=AdminState.activate_user(u["id"]),
                    size="1",
                    color_scheme="green",
                    variant="outline",
                ),
                rx.button(
                    "Suspender",
                    on_click=AdminState.suspend_user(u["id"]),
                    size="1",
                    color_scheme="orange",
                    variant="outline",
                ),
                spacing="2",
            ),
            align="center",
            justify="between",
            width="100%",
        ),
        width="100%",
    )


def _estudo_card(e: dict) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(e["titulo"], font_weight="bold", size="3"),
                rx.spacer(),
                rx.badge(e["status"], color_scheme="orange", variant="soft"),
                justify="between",
                width="100%",
            ),
            rx.text(e["descricao"], color="gray", size="2"),
            rx.hstack(
                rx.button(
                    "Aprovar",
                    on_click=AdminState.aprovar_estudo(e["id"]),
                    size="1",
                    color_scheme="green",
                ),
                rx.button(
                    "Rejeitar",
                    on_click=AdminState.rejeitar_estudo(e["id"]),
                    size="1",
                    color_scheme="red",
                    variant="outline",
                ),
                spacing="2",
            ),
            spacing="2",
            width="100%",
        ),
        width="100%",
    )


def _lead_card(l: dict) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(l["nome"], font_weight="bold", size="3"),
                rx.text(l["email"], color="gray", size="2"),
                spacing="0",
            ),
            rx.spacer(),
            rx.badge(l["status"], color_scheme="blue", variant="soft"),
            align="center",
            justify="between",
            width="100%",
        ),
        width="100%",
    )


# ── Tabs ──────────────────────────────────────────────────────────────────────

def _gestores_tab() -> rx.Component:
    return rx.vstack(
        # Formulário de criação
        rx.card(
            rx.vstack(
                rx.heading("Criar Novo Gestor", size="4"),
                rx.input(
                    placeholder="Nome completo",
                    value=AdminState.new_gestor_nome,
                    on_change=AdminState.set_new_gestor_nome,
                    size="3",
                ),
                rx.input(
                    placeholder="Email",
                    value=AdminState.new_gestor_email,
                    on_change=AdminState.set_new_gestor_email,
                    type="email",
                    size="3",
                ),
                rx.text(
                    "Senha inicial: senha123 (usuário deverá alterar no primeiro acesso)",
                    color="gray",
                    size="2",
                ),
                rx.button(
                    "Criar Gestor",
                    on_click=AdminState.create_gestor,
                    color_scheme="violet",
                    on_mount=AdminState.load_gestores,
                ),
                rx.cond(
                    AdminState.message != "",
                    rx.callout(
                        AdminState.message,
                        variant="soft",
                        color_scheme=rx.cond(
                            AdminState.message_type == "success",
                            "green",
                            "red",
                        ),
                    ),
                ),
                spacing="3",
            ),
            width="100%",
        ),
        rx.divider(),
        rx.heading("Gestores Cadastrados", size="4"),
        rx.foreach(
            AdminState.gestores.to(list[dict[str, str]]),
            _user_card,
        ),
        spacing="3",
        width="100%",
    )


def _coordenadores_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("Coordenadores Cadastrados", size="4"),
        rx.foreach(
            AdminState.coordenadores.to(list[dict[str, str]]),
            _user_card,
        ),
        on_mount=AdminState.load_coordenadores,
        spacing="3",
        width="100%",
    )


def _estudos_tab() -> rx.Component:
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.text("Motivo da rejeição (usado ao clicar em Rejeitar):", size="2"),
                rx.text_area(
                    placeholder="Explique o motivo da rejeição",
                    value=AdminState.reject_motivo,
                    on_change=AdminState.set_reject_motivo,
                    width="100%",
                ),
                spacing="2",
            ),
            width="100%",
        ),
        rx.cond(
            AdminState.message != "",
            rx.callout(
                AdminState.message,
                variant="soft",
                color_scheme=rx.cond(
                    AdminState.message_type == "success",
                    "green",
                    rx.cond(AdminState.message_type == "error", "red", "blue"),
                ),
            ),
        ),
        rx.divider(),
        rx.heading("Estudos Pendentes de Avaliação", size="4"),
        rx.cond(
            AdminState.estudos_pendentes.length() > 0,
            rx.foreach(
                AdminState.estudos_pendentes.to(list[dict[str, str]]),
                _estudo_card,
            ),
            rx.text("Nenhum estudo pendente de avaliação.", color="gray"),
        ),
        on_mount=AdminState.load_estudos_pendentes,
        spacing="3",
        width="100%",
    )


def _leads_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("Leads — Cadastros de Interesse", size="4"),
        rx.cond(
            AdminState.leads.length() > 0,
            rx.foreach(
                AdminState.leads.to(list[dict[str, str]]),
                _lead_card,
            ),
            rx.text("Nenhum lead cadastrado ainda.", color="gray"),
        ),
        on_mount=AdminState.load_leads,
        spacing="3",
        width="100%",
    )
