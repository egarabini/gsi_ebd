import reflex as rx

from .landing_content.controller import landing_page_full, LandingState
from .pages.login import login_page
from .pages.admin import admin_page
from .pages.gestor import gestor_page
from .pages.aluno import aluno_page
from .pages.lesson import lesson_page
from .pages.coordenador import coordenador_page
from .pages.perfil import alterar_senha_page
from .states.auth import AuthState
from .states.admin import AdminState
from .states.gestor import GestorState
from .states.aluno import AlunoState
from .states.coordenador import CoordenadorState
from .states.perfil import PerfilState
from .states.common import CommonState
from .models.user import User, UserStatus
from .models.study import Study, StudyVersion
from .models.progress import UserResponse, Progress
from .models.subscription import Subscription, PaymentHistory
from .models.lead import Lead
from .models.site_content import Testemunho, SiteConfig
from .models.notification import Notification


app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)


# ── Rota raiz: Landing Page Pública ─────────────────────────────────────────
app.add_page(
    landing_page_full,
    route="/",
    title="GSI-EBD — Estudos Bíblicos Dirigidos",
    on_load=LandingState.load_content,
)

# ── Autenticação ──────────────────────────────────────────────────────────────
app.add_page(login_page, route="/login", title="GSI-EBD — Login")

# ── Confirmação de conta via token (email) ────────────────────────────────────
app.add_page(
    lambda: rx.center(
        rx.card(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Confirmando sua conta...", color="gray"),
                spacing="3",
                align="center",
                padding="2rem",
            )
        ),
        height="100vh",
    ),
    route="/confirmar/[token]",
    title="GSI-EBD — Confirmação",
    on_load=AuthState.confirm_account_token,
)

# ── Admin ─────────────────────────────────────────────────────────────────────
app.add_page(
    admin_page,
    route="/admin",
    title="GSI-EBD — Admin",
    on_load=[AuthState.check_auth, AdminState.load_gestores, AdminState.load_coordenadores],
)

# ── Gestor ────────────────────────────────────────────────────────────────────
app.add_page(
    gestor_page,
    route="/gestor",
    title="GSI-EBD — Gestor",
    on_load=[AuthState.check_auth, GestorState.load_all],
)

# ── Aluno ─────────────────────────────────────────────────────────────────────
app.add_page(
    aluno_page,
    route="/aluno",
    title="GSI-EBD — Meus Estudos",
    on_load=[AuthState.check_auth, AlunoState.load_assigned_studies],
)

app.add_page(
    lesson_page,
    route="/aluno/licao",
    title="GSI-EBD — Lição",
    on_load=[AuthState.check_auth],
)

# ── Coordenador ────────────────────────────────────────────────────────────────────────────────
app.add_page(
    coordenador_page,
    route="/coordenador",
    title="GSI-EBD — Coordenador",
    on_load=[AuthState.check_auth, CoordenadorState.load_all],
)

# ── Perfil / Alterar Senha ────────────────────────────────────────────────────────────────────
app.add_page(
    alterar_senha_page,
    route="/perfil/alterar-senha",
    title="GSI-EBD — Alterar Senha",
    on_load=[PerfilState.check_perfil_auth],
)
