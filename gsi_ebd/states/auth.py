from typing import Optional

import reflex as rx
from passlib.context import CryptContext

from ..models.user import User, Role

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthState(rx.State):
    is_authenticated: bool = False
    current_user_id: Optional[int] = None
    current_user_name: str = ""
    current_user_role: int = Role.ALUNO
    login_error: str = ""
    register_error: str = ""

    login_email: str = ""
    login_password: str = ""
    register_nome: str = ""
    register_email: str = ""
    register_password: str = ""

    @rx.var
    def is_admin(self) -> bool:
        return self.current_user_role == Role.ADMIN

    @rx.var
    def is_supervisor(self) -> bool:
        return self.current_user_role == Role.SUPERVISOR

    @rx.var
    def is_gestor(self) -> bool:
        return self.current_user_role == Role.GESTOR

    @rx.var
    def is_aluno(self) -> bool:
        return self.current_user_role == Role.ALUNO

    @rx.var
    def redirect_path(self) -> str:
        if not self.is_authenticated:
            return "/login"
        role_paths = {
            Role.ADMIN: "/admin",
            Role.SUPERVISOR: "/supervisor",
            Role.GESTOR: "/gestor",
            Role.ALUNO: "/aluno",
        }
        return role_paths.get(self.current_user_role, "/aluno")

    def login(self):
        self.login_error = ""
        with rx.session() as session:
            user = session.exec(
                User.select().where(User.email == self.login_email)
            ).first()
            if user and pwd_context.verify(self.login_password, user.password_hash):
                self.is_authenticated = True
                self.current_user_id = user.id
                self.current_user_name = user.nome
                self.current_user_role = user.role
                return rx.redirect(self.redirect_path)
            self.login_error = "Email ou senha invalidos"

    def register(self):
        self.register_error = ""
        with rx.session() as session:
            existing = session.exec(
                User.select().where(User.email == self.register_email)
            ).first()
            if existing:
                self.register_error = "Email ja cadastrado"
                return
            hashed = pwd_context.hash(self.register_password)
            user = User(
                email=self.register_email,
                password_hash=hashed,
                nome=self.register_nome,
                role=Role.ALUNO,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            self.is_authenticated = True
            self.current_user_id = user.id
            self.current_user_name = user.nome
            self.current_user_role = user.role
            return rx.redirect("/aluno")

    def logout(self):
        self.is_authenticated = False
        self.current_user_id = None
        self.current_user_name = ""
        self.current_user_role = Role.ALUNO
        self.login_email = ""
        self.login_password = ""
        return rx.redirect("/login")

    def check_auth(self):
        if not self.is_authenticated:
            return rx.redirect("/login")
