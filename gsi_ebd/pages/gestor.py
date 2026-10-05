"""Painel do Gestor — Supervisores, Alunos, Estudos Aprovados, Proposta, Meus Estudos."""
import reflex as rx
from ..states.gestor import GestorState
from ..components.navbar import navbar
from ..components.sidebar import sidebar


# ── Utilitários ───────────────────────────────────────────────────────────────

def _metric_card(icon: str, label: str, value: rx.Var, color: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.box(
                rx.icon(icon, size=20, color="white"),
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
        padding="1rem",
        width="100%",
        _hover={"box_shadow": "0 4px 12px rgba(0,0,0,0.08)", "transform": "translateY(-1px)"},
        transition="all 0.2s",
    )


def _status_badge(status: rx.Var) -> rx.Component:
    return rx.badge(
        status,
        color_scheme=rx.cond(
            status == "ativo", "green",
            rx.cond(status == "suspenso", "orange", "gray"),
        ),
        variant="soft",
        radius="full",
        size="1",
    )


def _avatar(nome_base: rx.Var, color: str = "linear-gradient(135deg,#7c3aed,#4f46e5)") -> rx.Component:
    return rx.box(
        rx.text(nome_base[0], weight="bold", size="3", color="white"),
        bg=color,
        border_radius="50%",
        width="2.2rem",
        height="2.2rem",
        display="flex",
        align_items="center",
        justify_content="center",
        flex_shrink="0",
    )


def _message_callout() -> rx.Component:
    return rx.cond(
        GestorState.message != "",
        rx.callout(
            GestorState.message,
            color_scheme=rx.cond(
                GestorState.message_type == "success", "green",
                rx.cond(GestorState.message_type == "error", "red", "blue"),
            ),
            variant="soft",
            size="2",
        ),
    )


# ── Tab 1: Supervisores ───────────────────────────────────────────────────────

def _supervisor_row(s: dict) -> rx.Component:
    return rx.card(
        rx.hstack(
            _avatar(s["nome_base"], "linear-gradient(135deg,#059669,#10b981)"),
            rx.vstack(
                rx.text(s["nome"], weight="bold", size="3"),
                rx.text(s["email"], color="gray", size="1"),
                spacing="0",
                align="start",
                flex="1",
            ),
            rx.spacer(),
            _status_badge(s["status"]),
            rx.cond(
                s["status"] != "ativo",
                rx.button(
                    rx.icon("user-check", size=13),
                    "Ativar",
                    on_click=GestorState.activate_supervisor(s["id"]),
                    size="1",
                    color_scheme="green",
                    variant="soft",
                ),
            ),
            align="center",
            spacing="3",
            width="100%",
        ),
        padding="0.9rem",
        width="100%",
        border_radius="0.75rem",
    )


def _supervisores_tab() -> rx.Component:
    return rx.vstack(
        # Formulário de criação
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("user-plus", size=18, color="#7c3aed"),
                    rx.heading("Adicionar Supervisor", size="4", color="#1e1b4b"),
                    spacing="2", align="center",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Nome completo",
                        value=GestorState.new_supervisor_nome,
                        on_change=GestorState.set_new_supervisor_nome,
                        size="3", width="100%",
                    ),
                    rx.input(
                        placeholder="Email",
                        value=GestorState.new_supervisor_email,
                        on_change=GestorState.set_new_supervisor_email,
                        type="email",
                        size="3", width="100%",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.icon("info", size=14, color="gray"),
                    rx.text("Senha inicial: senha123 — supervisor deverá alterar no 1º acesso",
                            color="gray", size="1"),
                    spacing="1", align="center",
                ),
                rx.button(
                    rx.icon("user-plus", size=15),
                    "Criar Supervisor",
                    on_click=GestorState.create_supervisor,
                    color_scheme="green",
                    size="2",
                ),
                _message_callout(),
                spacing="3", width="100%",
            ),
            padding="1.2rem", width="100%",
        ),

        rx.divider(),
        rx.hstack(
            rx.heading("Supervisores Cadastrados", size="4", color="#1e1b4b"),
            rx.spacer(),
            rx.text(GestorState.total_supervisores.to(str) + " supervisor(es)",
                    color="gray", size="2"),
            align="center", width="100%",
        ),
        rx.cond(
            GestorState.has_supervisores,
            rx.vstack(
                rx.foreach(
                    GestorState.supervisores.to(list[dict[str, str]]),
                    _supervisor_row,
                ),
                spacing="2", width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("users", size=40, color="var(--gray-5)"),
                    rx.text("Nenhum supervisor cadastrado ainda.", color="gray", size="2"),
                    spacing="2", align="center",
                ),
                padding="2rem",
            ),
        ),
        on_mount=GestorState.load_supervisores,
        spacing="3", width="100%",
    )


# ── Tab 2: Alunos ─────────────────────────────────────────────────────────────

def _aluno_row(a: dict) -> rx.Component:
    is_selected = GestorState.selected_aluno_ids.contains(a["id"].to(int))
    return rx.card(
        rx.hstack(
            rx.checkbox(
                checked=is_selected,
                on_change=GestorState.toggle_aluno(a["id"]),
                color_scheme="violet",
            ),
            _avatar(a["nome_base"]),
            rx.vstack(
                rx.text(a["nome"], weight="bold", size="3"),
                rx.text(a["email"], color="gray", size="1"),
                spacing="0", align="start", flex="1",
            ),
            rx.spacer(),
            _status_badge(a["status"]),
            rx.cond(
                a["status"] != "ativo",
                rx.button(
                    rx.icon("user-check", size=13),
                    "Ativar",
                    on_click=GestorState.activate_aluno(a["id"]),
                    size="1",
                    color_scheme="green",
                    variant="soft",
                ),
            ),
            align="center", spacing="3", width="100%",
        ),
        padding="0.9rem",
        width="100%",
        border_radius="0.75rem",
        border=rx.cond(is_selected, "2px solid #7c3aed", "1px solid var(--gray-4)"),
        bg=rx.cond(is_selected, "rgba(124,58,237,0.04)", "white"),
        transition="all 0.15s",
        _hover={"border_color": "#7c3aed"},
    )


def _alunos_tab() -> rx.Component:
    return rx.vstack(
        # Formulário de criação
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("user-plus", size=18, color="#7c3aed"),
                    rx.heading("Adicionar Aluno", size="4", color="#1e1b4b"),
                    spacing="2", align="center",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Nome completo",
                        value=GestorState.new_aluno_nome,
                        on_change=GestorState.set_new_aluno_nome,
                        size="3", width="100%",
                    ),
                    rx.input(
                        placeholder="Email",
                        value=GestorState.new_aluno_email,
                        on_change=GestorState.set_new_aluno_email,
                        type="email",
                        size="3", width="100%",
                    ),
                    columns="2",
                    spacing="3", width="100%",
                ),
                rx.hstack(
                    rx.icon("info", size=14, color="gray"),
                    rx.text("Senha inicial: senha123 — aluno deverá alterar no 1º acesso",
                            color="gray", size="1"),
                    spacing="1", align="center",
                ),
                rx.button(
                    rx.icon("user-plus", size=15),
                    "Criar Aluno",
                    on_click=GestorState.create_aluno,
                    color_scheme="violet",
                    size="2",
                ),
                _message_callout(),
                spacing="3", width="100%",
            ),
            padding="1.2rem", width="100%",
        ),

        rx.divider(),
        rx.hstack(
            rx.heading("Alunos da Equipe", size="4", color="#1e1b4b"),
            rx.spacer(),
            rx.hstack(
                rx.text(GestorState.total_alunos.to(str) + " aluno(s)", color="gray", size="2"),
                rx.button(
                    "Selecionar todos",
                    on_click=GestorState.select_all_alunos,
                    variant="ghost", color_scheme="violet", size="1",
                ),
                rx.button(
                    "Limpar",
                    on_click=GestorState.clear_selection,
                    variant="ghost", color_scheme="gray", size="1",
                ),
                spacing="2", align="center",
            ),
            align="center", width="100%",
        ),
        rx.cond(
            GestorState.has_alunos,
            rx.vstack(
                rx.foreach(
                    GestorState.alunos.to(list[dict[str, str]]),
                    _aluno_row,
                ),
                spacing="2", width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("graduation-cap", size=40, color="var(--gray-5)"),
                    rx.text("Nenhum aluno cadastrado ainda.", color="gray", size="2"),
                    spacing="2", align="center",
                ),
                padding="2rem",
            ),
        ),
        on_mount=GestorState.load_alunos,
        spacing="3", width="100%",
    )


# ── Tab 3: Estudos Aprovados + Atribuição ─────────────────────────────────────

def _estudo_aprovado_row(e: dict) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(e["titulo"], weight="bold", size="3"),
                rx.text(e["descricao"], color="gray", size="1"),
                spacing="0", align="start", flex="1",
            ),
            rx.spacer(),
            rx.vstack(
                rx.badge(e["nivel"], color_scheme="violet", variant="soft", size="1"),
                rx.badge("Aprovado", color_scheme="green", variant="soft", size="1"),
                spacing="1", align="end",
            ),
            align="center", spacing="3", width="100%",
        ),
        padding="0.9rem", width="100%", border_radius="0.75rem",
    )


def _estudos_tab() -> rx.Component:
    return rx.vstack(
        # Painel de atribuição
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("send", size=18, color="#7c3aed"),
                    rx.heading("Atribuir Estudo aos Alunos", size="4", color="#1e1b4b"),
                    spacing="2", align="center",
                ),
                rx.cond(
                    GestorState.selected_aluno_ids.length() > 0,
                    rx.callout(
                        GestorState.selected_aluno_ids.length().to(str) + " aluno(s) selecionado(s) na aba Alunos",
                        color_scheme="violet", variant="soft", size="1",
                    ),
                    rx.text("← Selecione alunos na aba 'Alunos' antes de atribuir.", color="gray", size="2"),
                ),
                rx.select(
                    GestorState.study_options,
                    placeholder="Escolha um estudo aprovado...",
                    value=GestorState.selected_study_id,
                    on_change=GestorState.set_selected_study_id,
                    width="100%",
                    disabled=~GestorState.has_estudos_aprovados,
                ),
                rx.button(
                    rx.icon("send", size=15),
                    "Atribuir Estudo",
                    on_click=GestorState.assign_study,
                    color_scheme="violet",
                    size="2",
                    width="100%",
                    disabled=GestorState.selected_aluno_ids.length() == 0,
                ),
                _message_callout(),
                spacing="3", width="100%",
            ),
            padding="1.2rem", width="100%",
        ),

        rx.divider(),
        rx.hstack(
            rx.heading("Estudos Aprovados Disponíveis", size="4", color="#1e1b4b"),
            rx.spacer(),
            rx.text(GestorState.total_estudos_ativos.to(str) + " estudo(s)",
                    color="gray", size="2"),
            align="center", width="100%",
        ),
        rx.cond(
            GestorState.has_estudos_aprovados,
            rx.vstack(
                rx.foreach(
                    GestorState.estudos_aprovados.to(list[dict[str, str]]),
                    _estudo_aprovado_row,
                ),
                spacing="2", width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("book-open", size=40, color="var(--gray-5)"),
                    rx.text("Nenhum estudo aprovado disponível.", color="gray", size="2"),
                    rx.text("Proponha um estudo na aba 'Propor Estudo'.",
                            color="gray", size="1"),
                    spacing="2", align="center",
                ),
                padding="2rem",
            ),
        ),
        on_mount=GestorState.load_estudos_aprovados,
        spacing="3", width="100%",
    )


# ── Tab 4: Propor Estudo ──────────────────────────────────────────────────────

def _estudo_proposto_row(e: dict) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(e["titulo"], weight="bold", size="3"),
                rx.text(e["descricao"], color="gray", size="1"),
                spacing="0", align="start", flex="1",
            ),
            rx.spacer(),
            rx.vstack(
                rx.badge(e["nivel"], color_scheme="violet", variant="soft", size="1"),
                rx.badge(
                    e["status"],
                    color_scheme=rx.cond(
                        e["status"].contains("APROVADO"), "green",
                        rx.cond(e["status"].contains("REJEITADO"), "red", "orange"),
                    ),
                    variant="soft", size="1",
                ),
                spacing="1", align="end",
            ),
            align="center", spacing="3", width="100%",
        ),
        padding="0.9rem", width="100%", border_radius="0.75rem",
    )


def _propor_tab() -> rx.Component:
    return rx.vstack(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("file-plus", size=18, color="#7c3aed"),
                    rx.heading("Propor Novo Estudo", size="4", color="#1e1b4b"),
                    spacing="2", align="center",
                ),
                rx.text(
                    "Envie sua proposta ao Administrador. Após aprovação, o estudo fica disponível para atribuição.",
                    color="gray", size="2",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Título do estudo",
                        value=GestorState.new_study_title,
                        on_change=GestorState.set_new_study_title,
                        size="3", width="100%",
                    ),
                    rx.input(
                        placeholder="Descrição curta",
                        value=GestorState.new_study_description,
                        on_change=GestorState.set_new_study_description,
                        size="3", width="100%",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.grid(
                    rx.input(
                        placeholder="Categoria (ex: evangelismo)",
                        value=GestorState.new_study_category,
                        on_change=GestorState.set_new_study_category,
                        size="3", width="100%",
                    ),
                    rx.select(
                        GestorState.study_levels,
                        placeholder="Nível",
                        value=GestorState.new_study_level,
                        on_change=GestorState.set_new_study_level,
                        width="100%",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.text_area(
                    placeholder="Conteúdo do estudo (Markdown)...",
                    value=GestorState.new_study_content_md,
                    on_change=GestorState.set_new_study_content_md,
                    width="100%",
                    rows="10",
                ),
                rx.button(
                    rx.icon("send", size=15),
                    "Enviar para Avaliação",
                    on_click=GestorState.propor_estudo,
                    color_scheme="violet",
                    size="2",
                ),
                _message_callout(),
                spacing="3", width="100%",
            ),
            padding="1.2rem", width="100%",
        ),

        rx.divider(),
        rx.heading("Meus Estudos Propostos", size="4", color="#1e1b4b"),
        rx.cond(
            GestorState.estudos_propostos.length() > 0,
            rx.vstack(
                rx.foreach(
                    GestorState.estudos_propostos.to(list[dict[str, str]]),
                    _estudo_proposto_row,
                ),
                spacing="2", width="100%",
            ),
            rx.center(
                rx.text("Nenhum estudo proposto ainda.", color="gray", size="2"),
                padding="2rem",
            ),
        ),
        on_mount=GestorState.load_estudos_propostos,
        spacing="3", width="100%",
    )


# ── Página principal ──────────────────────────────────────────────────────────

def gestor_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                # Cabeçalho
                rx.hstack(
                    rx.vstack(
                        rx.heading("Painel do Gestor", size="7", weight="bold", color="#1e1b4b"),
                        rx.text("Gerencie sua equipe de supervisores e alunos.",
                                color="gray", size="2"),
                        spacing="0", align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh-cw", size=15),
                        "Atualizar",
                        on_click=GestorState.load_all,
                        variant="soft", color_scheme="violet", size="2",
                    ),
                    align="center", width="100%",
                ),

                # Métricas
                rx.grid(
                    _metric_card("users", "Supervisores",
                                 GestorState.total_supervisores.to(str),
                                 "linear-gradient(135deg,#059669,#10b981)"),
                    _metric_card("graduation-cap", "Alunos",
                                 GestorState.total_alunos.to(str),
                                 "linear-gradient(135deg,#7c3aed,#4f46e5)"),
                    _metric_card("book-open", "Estudos Disponíveis",
                                 GestorState.total_estudos_ativos.to(str),
                                 "linear-gradient(135deg,#d97706,#f59e0b)"),
                    _metric_card("clock", "Estudos em Avaliação",
                                 GestorState.total_pendentes.to(str),
                                 "linear-gradient(135deg,#dc2626,#ef4444)"),
                    columns="4", spacing="4", width="100%",
                ),

                # Abas
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger(
                            rx.hstack(rx.icon("eye", size=14), rx.text("Supervisores"), spacing="1"),
                            value="supervisores",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(rx.icon("graduation-cap", size=14), rx.text("Alunos"), spacing="1"),
                            value="alunos",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(rx.icon("book-open", size=14), rx.text("Estudos Aprovados"), spacing="1"),
                            value="estudos",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(rx.icon("file-plus", size=14), rx.text("Propor Estudo"), spacing="1"),
                            value="propor",
                        ),
                    ),
                    rx.tabs.content(_supervisores_tab(), value="supervisores"),
                    rx.tabs.content(_alunos_tab(), value="alunos"),
                    rx.tabs.content(_estudos_tab(), value="estudos"),
                    rx.tabs.content(_propor_tab(), value="propor"),
                    default_value="alunos",
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
        on_mount=GestorState.load_all,
    )
