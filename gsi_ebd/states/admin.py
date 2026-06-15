from typing import List, Optional

import reflex as rx

from ..models.user import User, Role
from .auth import AuthState


class AdminState(AuthState):
    new_gestor_nome: str = ""
    new_gestor_email: str = ""
    new_gestor_password: str = ""
    new_supervisor_nome: str = ""
    new_supervisor_email: str = ""
    new_supervisor_password: str = ""
    gestores: List[User] = []
    supervisores: List[User] = []
    message: str = ""
    message_type: str = "info"

    def load_gestores(self):
        with rx.session() as session:
            self.gestores = session.exec(
                User.select().where(User.role == Role.GESTOR)
            ).all()

    def load_supervisores(self):
        with rx.session() as session:
            self.supervisores = session.exec(
                User.select().where(User.role == Role.SUPERVISOR)
            ).all()

    def create_gestor(self):
        if not self.is_admin:
            return rx.redirect("/login")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with rx.session() as session:
            existing = session.exec(
                User.select().where(User.email == self.new_gestor_email)
            ).first()
            if existing:
                self.message = "Email ja cadastrado"
                self.message_type = "error"
                return
            hashed = pwd_context.hash(self.new_gestor_password)
            user = User(
                email=self.new_gestor_email,
                password_hash=hashed,
                nome=self.new_gestor_nome,
                role=Role.GESTOR,
            )
            session.add(user)
            session.commit()
            self.message = "Gestor criado com sucesso"
            self.message_type = "success"
            self.new_gestor_nome = ""
            self.new_gestor_email = ""
            self.new_gestor_password = ""
            self.load_gestores()

    def create_supervisor(self):
        if not self.is_admin:
            return rx.redirect("/login")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with rx.session() as session:
            existing = session.exec(
                User.select().where(User.email == self.new_supervisor_email)
            ).first()
            if existing:
                self.message = "Email ja cadastrado"
                self.message_type = "error"
                return
            hashed = pwd_context.hash(self.new_supervisor_password)
            user = User(
                email=self.new_supervisor_email,
                password_hash=hashed,
                nome=self.new_supervisor_nome,
                role=Role.SUPERVISOR,
            )
            session.add(user)
            session.commit()
            self.message = "Supervisor criado com sucesso"
            self.message_type = "success"
            self.new_supervisor_nome = ""
            self.new_supervisor_email = ""
            self.new_supervisor_password = ""
            self.load_supervisores()

    def deactivate_user(self, user_id: int):
        with rx.session() as session:
            user = session.exec(User.select().where(User.id == user_id)).first()
            if user:
                user.is_active = False
                session.add(user)
                session.commit()
        self.load_gestores()
        self.load_supervisores()
