"""Painel do Coordenador — acompanha e atribui estudos aos seus alunos."""
import reflex as rx
from ..states.coordenador import CoordenadorState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


# ── Paleta de cores por status ────────────────────────────────────────────────
def _status_badge(status: rx.Var) -> rx.Component:
    return rx.badge(
        status,
        color_scheme=rx.cond(
            status == "ativo", "green",
            rx.cond(status == "suspenso", "orange", "gray"),
        ),
        variant="soft",
        radius="full",
    )


# ── Cartão de métrica ─────────────────────────────────────────────────────────
def _metric_card(icon: str, label: str, value: rx.Var, color: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=22, color="white"),
                bg=color,
                border_radius="0.75rem",
                padding="0.6rem",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text(label, size="1", color="gray", weight="medium"),
                rx.text(value, size="6", weight="bold", color="#1e1b4b"),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        padding="1.2rem",
        width="100%",
        box_shadow="0 1px 4px rgba(0,0,0,0.06)",
        _hover={"box_shadow": "0 4px 12px rgba(0,0,0,0.1)", "transform": "translateY(-1px)"},
        transition="all 0.2s",
    )


# ── Card de aluno ─────────────────────────────────────────────────────────────
def _aluno_card(a: dict) -> rx.Component:
    is_selected = CoordenadorState.selected_aluno_ids.contains(a["id"].to(int))
    return rx.card(
        rx.hstack(
            # Checkbox de seleção
            rx.checkbox(
                checked=is_selected,
                on_change=CoordenadorState.toggle_aluno(a["id"]),
                color_scheme="violet",
            ),
            # Avatar inicial
            rx.box(
                rx.text(
                    a["nome_base"].to(str)[0],
                    weight="bold",
                    size="4",
                    color="white",
                ),
                bg="linear-gradient(135deg, #7c3aed, #4f46e5)",
                border_radius="50%",
                width="2.5rem",
                height="2.5rem",
                display="flex",
                align_items="center",
                justify_content="center",
                flex_shrink="0",
            ),
            # Info
            rx.vstack(
                rx.text(a["nome"], weight="bold", size="3"),
                rx.text(a["email"], color="gray", size="1"),
                spacing="0",
                align="start",
                flex="1",
            ),
            rx.spacer(),
            # Progresso
            rx.vstack(
                rx.hstack(
                    rx.text(a["estudos_concluidos"], weight="bold", color="#7c3aed"),
                    rx.text("/", color="gray"),
                    rx.text(a["estudos_total"], color="gray"),
                    rx.text("estudos", size="1", color="gray"),
                    spacing="1",
                    align="center",
                ),
                rx.progress(
                    value=a["progresso"].to(int),
                    width="8rem",
                    color_scheme="violet",
                    size="1",
                ),
                rx.text(a["progresso"] + "%", size="1", color="gray"),
                spacing="1",
                align="center",
            ),
            rx.spacer(),
            _status_badge(a["status"]),
            align="center",
            width="100%",
            spacing="3",
        ),
        width="100%",
        padding="1rem",
        border=rx.cond(
            is_selected,
            "2px solid #7c3aed",
            "1px solid var(--gray-4)",
        ),
        border_radius="0.75rem",
        bg=rx.cond(is_selected, "rgba(124, 58, 237, 0.04)", "white"),
        cursor="pointer",
        transition="all 0.15s",
        _hover={"border_color": "#7c3aed", "box_shadow": "0 2px 8px rgba(124,58,237,0.1)"},
    )


# ── Seção de alunos ───────────────────────────────────────────────────────────
def _alunos_section() -> rx.Component:
    return rx.vstack(
        # Header da seção
        rx.hstack(
            rx.heading("Meus Alunos", size="5", color="#1e1b4b"),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("check-square", size=14),
                    "Selecionar todos",
                    on_click=CoordenadorState.select_all_alunos,
                    variant="soft",
                    color_scheme="violet",
                    size="1",
                ),
                rx.button(
                    rx.icon("x", size=14),
                    "Limpar",
                    on_click=CoordenadorState.clear_selection,
                    variant="ghost",
                    color_scheme="gray",
                    size="1",
                ),
                spacing="2",
            ),
        ),
        rx.cond(
            CoordenadorState.has_alunos,
            rx.vstack(
                rx.foreach(
                    CoordenadorState.alunos.to(list[dict[str, str]]),
                    _aluno_card,
                ),
                spacing="2",
                width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("users", size=48, color="var(--gray-6)"),
                    rx.text(
                        "Nenhum aluno vinculado ainda.",
                        color="gray",
                        size="3",
                    ),
                    rx.text(
                        "Peça ao seu Gestor para vincular alunos à sua turma.",
                        color="gray",
                        size="2",
                    ),
                    spacing="2",
                    align="center",
                ),
                padding="3rem",
            ),
        ),
        spacing="3",
        width="100%",
    )


# ── Painel de atribuição ──────────────────────────────────────────────────────
def _assign_panel() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("book-open", size=18, color="#7c3aed"),
                rx.heading("Atribuir Estudo", size="4", color="#1e1b4b"),
                spacing="2",
                align="center",
            ),
            rx.divider(),
            # Contagem de selecionados
            rx.cond(
                CoordenadorState.selected_aluno_ids.length() > 0,
                rx.callout(
                    rx.text(
                        CoordenadorState.selected_aluno_ids.length().to(str)
                        + " aluno(s) selecionado(s)",
                    ),
                    icon="info",
                    color_scheme="violet",
                    variant="soft",
                    size="1",
                ),
                rx.text(
                    "Selecione alunos na lista ao lado para atribuir um estudo.",
                    color="gray",
                    size="2",
                ),
            ),
            # Select de estudo
            rx.select(
                CoordenadorState.study_options,
                placeholder="Escolha um estudo...",
                value=CoordenadorState.selected_study_option,
                on_change=CoordenadorState.set_selected_study_option,
                width="100%",
                disabled=~CoordenadorState.has_estudos,
            ),
            rx.cond(
                ~CoordenadorState.has_estudos,
                rx.text(
                    "Nenhum estudo aprovado disponível no momento.",
                    color="gray",
                    size="1",
                ),
                rx.fragment(),
            ),
            rx.button(
                rx.icon("send", size=16),
                "Atribuir Estudo",
                on_click=CoordenadorState.assign_study,
                color_scheme="violet",
                width="100%",
                size="3",
                disabled=(
                    CoordenadorState.selected_aluno_ids.length() == 0
                ),
            ),
            # Feedback
            rx.cond(
                CoordenadorState.message != "",
                rx.callout(
                    CoordenadorState.message,
                    icon=rx.cond(
                        CoordenadorState.message_type == "success",
                        "check-circle",
                        "alert-circle",
                    ),
                    color_scheme=rx.cond(
                        CoordenadorState.message_type == "success",
                        "green",
                        rx.cond(CoordenadorState.message_type == "error", "red", "blue"),
                    ),
                    variant="soft",
                    size="1",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        padding="1.5rem",
        width="100%",
        position="sticky",
        top="1rem",
        box_shadow="0 2px 12px rgba(0,0,0,0.08)",
        border_radius="1rem",
    )


# ── Seção de turmas ───────────────────────────────────────────────────────────
def _turmas_section() -> rx.Component:
    return rx.cond(
        CoordenadorState.turmas.length() > 0,
        rx.vstack(
            rx.heading("Minhas Turmas", size="4", color="#1e1b4b"),
            rx.foreach(
                CoordenadorState.turmas.to(list[dict[str, str]]),
                lambda t: rx.card(
                    rx.hstack(
                        rx.icon("users", size=16, color="#7c3aed"),
                        rx.vstack(
                            rx.text(t["nome"], weight="bold", size="2"),
                            rx.text(t["descricao"], color="gray", size="1"),
                            spacing="0",
                            align="start",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="0.8rem",
                    border_left="3px solid #7c3aed",
                    width="100%",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        rx.fragment(),
    )


# ── Página principal ──────────────────────────────────────────────────────────
def coordenador_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                # Título
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            "Painel do Coordenador",
                            size="7",
                            weight="bold",
                            color="#1e1b4b",
                        ),
                        rx.text(
                            "Acompanhe e impulsione o crescimento dos seus alunos.",
                            color="gray",
                            size="2",
                        ),
                        spacing="0",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh-cw", size=16),
                        "Atualizar",
                        on_click=CoordenadorState.load_all,
                        variant="soft",
                        color_scheme="violet",
                        size="2",
                    ),
                    align="center",
                    width="100%",
                ),

                # Métricas
                rx.grid(
                    _metric_card(
                        "users", "Total de Alunos",
                        CoordenadorState.total_alunos.to(str),
                        "linear-gradient(135deg, #7c3aed, #4f46e5)",
                    ),
                    _metric_card(
                        "user-check", "Alunos Ativos",
                        CoordenadorState.total_ativos.to(str),
                        "linear-gradient(135deg, #059669, #10b981)",
                    ),
                    _metric_card(
                        "trending-up", "Progresso Médio",
                        CoordenadorState.media_progresso_label,
                        "linear-gradient(135deg, #d97706, #f59e0b)",
                    ),
                    _metric_card(
                        "clock", "Pendências",
                        CoordenadorState.pendencias.to(str),
                        "linear-gradient(135deg, #dc2626, #ef4444)",
                    ),
                    columns="4",
                    spacing="4",
                    width="100%",
                ),

                # Layout principal: alunos | painel de atribuição
                rx.hstack(
                    # Coluna esquerda: lista de alunos
                    rx.box(
                        _alunos_section(),
                        flex="1",
                        min_width="0",
                    ),
                    # Coluna direita: atribuição + turmas
                    rx.vstack(
                        _assign_panel(),
                        _turmas_section(),
                        width="22rem",
                        flex_shrink="0",
                        spacing="4",
                    ),
                    align="start",
                    spacing="6",
                    width="100%",
                ),

                spacing="5",
                padding="2rem",
                width="100%",
                overflow_y="auto",
                height="calc(100vh - 52px)",
            ),
            spacing="0",
            width="100%",
            align="start",
        ),
        spacing="0",
        width="100%",
        height="100vh",
        bg="#f8f7ff",
    )
