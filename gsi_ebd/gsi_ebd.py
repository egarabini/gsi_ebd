import reflex as rx

from .pages.login import login_page
from .pages.admin import admin_page
from .pages.gestor import gestor_page
from .pages.aluno import aluno_page
from .pages.lesson import lesson_page
from .states.auth import AuthState
from .states.admin import AdminState
from .states.gestor import GestorState
from .states.aluno import AlunoState
from .states.common import CommonState
from .models.user import User
from .models.study import Study, StudyVersion
from .models.progress import UserResponse, Progress


app = rx.App(
    style={
        "font_family": "Inter, system-ui, sans-serif",
    },
)

app.add_page(login_page, route="/login", title="GSI-EBD - Login")

app.add_page(
    admin_page,
    route="/admin",
    title="GSI-EBD - Admin",
    on_load=[AuthState.check_auth, AdminState.load_gestores, AdminState.load_supervisores],
)

app.add_page(
    gestor_page,
    route="/gestor",
    title="GSI-EBD - Gestor",
    on_load=[AuthState.check_auth, GestorState.load_alunos, GestorState.load_studies],
)

app.add_page(
    aluno_page,
    route="/aluno",
    title="GSI-EBD - Aluno",
    on_load=[AuthState.check_auth, AlunoState.load_assigned_studies],
)

app.add_page(
    lesson_page,
    route="/aluno/licao",
    title="GSI-EBD - Licao",
    on_load=[AuthState.check_auth],
)

app.add_page(
    lambda: rx.center(rx.heading("Supervisor - Em breve", size="6")),
    route="/supervisor",
    title="GSI-EBD - Supervisor",
)
