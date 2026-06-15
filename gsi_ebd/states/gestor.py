from typing import List, Optional

import reflex as rx

from ..models.user import User, Role
from ..models.study import Study, StudyVersion, StudyAssignment
from .auth import AuthState


class GestorState(AuthState):
    new_aluno_nome: str = ""
    new_aluno_email: str = ""
    new_aluno_password: str = ""
    alunos: List[User] = []
    studies: List[Study] = []
    message: str = ""
    message_type: str = "info"
    selected_study_id: Optional[int] = None
    selected_aluno_ids: List[int] = []

    def load_alunos(self):
        with rx.session() as session:
            self.alunos = session.exec(
                User.select().where(
                    User.role == Role.ALUNO,
                    User.gestor_id == self.current_user_id,
                    User.is_active == True,
                )
            ).all()

    def load_studies(self):
        with rx.session() as session:
            self.studies = session.exec(
                Study.select().where(Study.is_active == True)
            ).all()

    def create_aluno(self):
        if not self.is_gestor:
            return rx.redirect("/login")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with rx.session() as session:
            existing = session.exec(
                User.select().where(User.email == self.new_aluno_email)
            ).first()
            if existing:
                self.message = "Email ja cadastrado"
                self.message_type = "error"
                return
            hashed = pwd_context.hash(self.new_aluno_password)
            user = User(
                email=self.new_aluno_email,
                password_hash=hashed,
                nome=self.new_aluno_nome,
                role=Role.ALUNO,
                gestor_id=self.current_user_id,
            )
            session.add(user)
            session.commit()
            self.message = "Aluno criado com sucesso"
            self.message_type = "success"
            self.new_aluno_nome = ""
            self.new_aluno_email = ""
            self.new_aluno_password = ""
            self.load_alunos()

    def assign_study(self):
        if not self.selected_study_id or not self.selected_aluno_ids:
            self.message = "Selecione um estudo e ao menos um aluno"
            self.message_type = "error"
            return
        with rx.session() as session:
            version = session.exec(
                StudyVersion.select()
                .where(StudyVersion.study_id == self.selected_study_id)
                .order_by(StudyVersion.version.desc())
            ).first()
            if not version:
                self.message = "Nenhuma versao disponivel para este estudo"
                self.message_type = "error"
                return
            for aluno_id in self.selected_aluno_ids:
                existing = session.exec(
                    StudyAssignment.select().where(
                        StudyAssignment.user_id == aluno_id,
                        StudyAssignment.study_id == self.selected_study_id,
                        StudyAssignment.study_version_id == version.id,
                    )
                ).first()
                if existing:
                    continue
                assignment = StudyAssignment(
                    user_id=aluno_id,
                    study_id=self.selected_study_id,
                    study_version_id=version.id,
                    assigned_by=self.current_user_id,
                )
                session.add(assignment)
            session.commit()
            self.message = "Estudo atribuido com sucesso"
            self.message_type = "success"

    def toggle_aluno_selection(self, aluno_id: int):
        if aluno_id in self.selected_aluno_ids:
            self.selected_aluno_ids = [
                i for i in self.selected_aluno_ids if i != aluno_id
            ]
        else:
            self.selected_aluno_ids = self.selected_aluno_ids + [aluno_id]
