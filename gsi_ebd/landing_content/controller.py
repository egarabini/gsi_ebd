"""
Controller da Landing Page — GSI-EBD.

Responsabilidades:
  1. Gerenciar o State do formulário de interesse (LandingState)
  2. Carregar textos dinâmicos do banco (SiteConfig)
  3. Carregar testemunhos ativos (Testemunho)
  4. Montar a página completa compondo todas as seções
  5. Salvar leads e disparar notificações

Uso em gsi_ebd.py:
    from .landing_content.controller import landing_page_full, LandingState
    app.add_page(landing_page_full, route="/", on_load=LandingState.load_content)
"""
from typing import Any

import reflex as rx
from sqlmodel import select

from ..models.lead import Lead, LeadStatus
from ..models.site_content import SiteConfig, Testemunho
from ..services.email_service import send_novo_lead_admin
from .sections import (
    hero_section,
    nome_section,
    sobre_section,
    niveis_section,
    testemunhos_section,
    formulario_section,
    rodape_section,
)




# ── State ────────────────────────────────────────────────────────────────────

class LandingState(rx.State):
    """Gerencia dados dinâmicos e formulário de interesse da landing page."""

    # Textos do banco (SiteConfig)
    hero_titulo: str = "Cresça na Palavra — A qualquer hora, em qualquer lugar"
    hero_subtitulo: str = "Uma plataforma de estudos bíblicos dirigidos, com acompanhamento personalizado."
    hero_cta: str = "Quero Participar"
    sobre_titulo: str = "Sobre a Plataforma GSI-EBD"
    sobre_texto: str = ""
    missao: str = ""
    visao: str = ""
    planos_descricao: str = ""
    rodape_email: str = ""
    rodape_telefone: str = ""
    redes_instagram: str = ""
    redes_youtube: str = ""
    redes_whatsapp: str = ""
    niveis_descricoes: dict[str, str] = {}

    # Testemunhos carregados do banco
    testemunhos: list[dict] = []

    @rx.var
    def tem_testemunhos(self) -> bool:
        return len(self.testemunhos) > 0

    # Formulário de interesse
    form_nome: str = ""
    form_email: str = ""
    form_telefone: str = ""
    form_cidade_estado: str = ""
    form_membro_igreja: bool = False
    form_nome_igreja: str = ""
    form_mensagem: str = ""
    form_error: str = ""
    form_success: bool = False
    form_loading: bool = False

    def load_content(self):
        """
        Carrega textos do SiteConfig e testemunhos do banco.
        Chamado via on_load da rota '/'.
        """
        with rx.session() as session:
            # Carrega todas as configurações de uma vez
            configs = session.exec(select(SiteConfig)).all()
            cfg = {c.chave: c.valor for c in configs}

            self.hero_titulo = cfg.get("hero_titulo", self.hero_titulo)
            self.hero_subtitulo = cfg.get("hero_subtitulo", self.hero_subtitulo)
            self.hero_cta = cfg.get("hero_cta_texto", self.hero_cta)
            self.sobre_titulo = cfg.get("sobre_titulo", self.sobre_titulo)
            self.sobre_texto = cfg.get("sobre_texto", self.sobre_texto)
            self.missao = cfg.get("missao_texto", self.missao)
            self.visao = cfg.get("visao_texto", self.visao)
            self.planos_descricao = cfg.get("planos_descricao", self.planos_descricao)
            self.rodape_email = cfg.get("rodape_email", self.rodape_email)
            self.rodape_telefone = cfg.get("rodape_telefone", self.rodape_telefone)
            self.redes_instagram = cfg.get("redes_instagram", "")
            self.redes_youtube = cfg.get("redes_youtube", "")
            self.redes_whatsapp = cfg.get("redes_whatsapp", "")

            # Descrições dos níveis
            self.niveis_descricoes = {
                k: cfg.get(k, "")
                for k in ["niveis_basico_desc", "niveis_medio_desc",
                          "niveis_avancado_desc", "niveis_master_desc"]
            }

            # Carrega testemunhos ativos ordenados e converte para TestemunhoItem
            raw = session.exec(
                select(Testemunho)
                .where(Testemunho.is_active == True)
                .order_by(Testemunho.ordem)
            ).all()
            self.testemunhos = [
                {
                    "id": t.id or 0,
                    "nome": t.nome,
                    "cidade": t.cidade,
                    "estado": t.estado,
                    "profissao_fe": t.profissao_fe,
                    "local": f"{t.cidade} / {t.estado}",
                    "texto": t.texto,
                }
                for t in raw
            ]

    def submit_form(self):
        """Valida e salva o formulário de interesse (Lead)."""
        self.form_error = ""

        # Validações básicas
        if not self.form_nome.strip():
            self.form_error = "Nome é obrigatório."
            return
        if not self.form_email.strip() or "@" not in self.form_email:
            self.form_error = "Informe um email válido."
            return

        self.form_loading = True
        yield  # atualiza UI (spinner)

        try:
            # Separa cidade e estado do campo combinado
            cidade_estado = self.form_cidade_estado.strip()
            cidade, estado = "", ""
            if "/" in cidade_estado:
                partes = cidade_estado.rsplit("/", 1)
                cidade = partes[0].strip()
                estado = partes[1].strip()
            else:
                cidade = cidade_estado

            with rx.session() as session:
                lead = Lead(
                    nome=self.form_nome.strip(),
                    email=self.form_email.strip().lower(),
                    telefone=self.form_telefone.strip(),
                    cidade=cidade,
                    estado=estado,
                    membro_igreja=self.form_membro_igreja,
                    nome_igreja=self.form_nome_igreja.strip(),
                    mensagem=self.form_mensagem.strip(),
                    status=LeadStatus.PENDENTE,
                )
                session.add(lead)
                session.commit()

            # Notifica Admin por email
            send_novo_lead_admin(
                admin_email="admin@gsi.ebd",  # será carregado do SiteConfig futuramente
                lead_nome=self.form_nome,
                lead_email=self.form_email,
            )

            # Limpa formulário
            self.form_nome = ""
            self.form_email = ""
            self.form_telefone = ""
            self.form_cidade_estado = ""
            self.form_membro_igreja = False
            self.form_nome_igreja = ""
            self.form_mensagem = ""
            self.form_success = True

        except Exception as e:
            self.form_error = f"Erro ao enviar. Tente novamente. ({e})"
        finally:
            self.form_loading = False


# ── Navbar da Landing Page ───────────────────────────────────────────────────

def _landing_navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Logo
            rx.hstack(
                rx.text("✝", font_size="1.4rem", color="#c7d2fe"),
                rx.heading("GSI-EBD", size="4", color="white"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            # Links de navegação
            rx.hstack(
                rx.link(rx.text("Sobre", color="rgba(255,255,255,0.8)", size="3"), href="#sobre"),
                rx.link(rx.text("Níveis", color="rgba(255,255,255,0.8)", size="3"), href="#niveis"),
                rx.link(rx.text("Depoimentos", color="rgba(255,255,255,0.8)", size="3"), href="#testemunhos"),
            rx.link(rx.text("Homenagens", color="rgba(255,255,255,0.8)", size="3"), href="/homenagens"),
                rx.link(
                    rx.button("Participar", size="2", variant="outline",
                              style={"border_color": "rgba(255,255,255,0.5)", "color": "white"}),
                    href="#formulario",
                ),
                rx.link(
                    rx.button("Entrar", size="2",
                              style={"background": "white", "color": "#4f46e5", "font_weight": "600"}),
                    href="/login",
                ),
                spacing="6",
                align="center",
                display=["none", "none", "flex"],
            ),
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding="0 2rem",
        ),
        style={
            "background": "rgba(15, 23, 42, 0.95)",
            "backdrop_filter": "blur(12px)",
            "border_bottom": "1px solid rgba(255,255,255,0.1)",
            "position": "fixed",
            "top": "0",
            "left": "0",
            "right": "0",
            "z_index": "100",
            "height": "64px",
            "display": "flex",
            "align_items": "center",
        },
    )


# ── Componente Principal (referenciado em gsi_ebd.py) ───────────────────────

def landing_page_full() -> rx.Component:
    """
    Monta a landing page completa compondo todas as seções.
    Cada seção é um componente independente em landing_content/sections/.
    O conteúdo dinâmico vem do LandingState que carrega do banco.
    """
    return rx.box(
        # Navbar fixo
        _landing_navbar(),
        # Espaçamento para compensar navbar fixo
        rx.box(height="64px"),
        # ── Seções ──────────────────────────────────────────
        hero_section(
            titulo=LandingState.hero_titulo,
            subtitulo=LandingState.hero_subtitulo,
            cta_texto=LandingState.hero_cta,
        ),
        sobre_section(
            titulo=LandingState.sobre_titulo,
            texto=LandingState.sobre_texto,
            missao=LandingState.missao,
            visao=LandingState.visao,
        ),
        nome_section(
            titulo=LandingState.sobre_titulo,
            texto=LandingState.sobre_texto,
        ),
        niveis_section(descricoes=LandingState.niveis_descricoes),
        testemunhos_section(state_cls=LandingState),
        formulario_section(
            state_class=LandingState,
            descricao=LandingState.planos_descricao,
        ),
        rodape_section(
            email=LandingState.rodape_email,
            telefone=LandingState.rodape_telefone,
            instagram=LandingState.redes_instagram,
            youtube=LandingState.redes_youtube,
            whatsapp=LandingState.redes_whatsapp,
        ),
        # ────────────────────────────────────────────────────
        width="100%",
        style={"scroll_behavior": "smooth"},
    )
