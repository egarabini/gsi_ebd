from typing import List

from sqlmodel import select
import reflex as rx

from ..models.user import User, Role
from ..models.study import Study, StudyAssignment
from ..models.progress import Progress
from ..models.turma import Turma, TurmaMembro
from ..services.study_service import StudyService
from .auth import AuthState


class CoordenadorState(AuthState):
    turmas: List[Turma] = []
    alunos: List[User] = []
    studies: List[Study] = []
    study_options: List[str] = []
    message: str = ""
    message_type: str = "info"
    selected_study_option: str = ""
    selected_aluno_ids: List[int] = []

    total_alunos: int = 0
    media_progresso: float = 0.0
    pendencias: int = 0

    def load_turmas(self):
        with rx.session() as session:
            self.turmas = session.exec(
                select(Turma).where(
                    Turma.coordenador_id == self.current_user_id,
                    Turma.is_active == True,
                )
            ).all()

    def load_alunos(self):
        with rx.session() as session:
            turma_ids = [t.id for t in self.turmas]
            if not turma_ids:
                self.alunos = []
                self.total_alunos = 0
                self.media_progresso = 0.0
                self.pendencias = 0
                return
            membros = session.exec(
                select(TurmaMembro).where(
                    TurmaMembro.turma_id.in_(turma_ids),
                    TurmaMembro.is_active == True,
                )
            ).all()
            aluno_ids = list({m.user_id for m in membros})
            if not aluno_ids:
                self.alunos = []
                self.total_alunos = 0
                self.media_progresso = 0.0
                self.pendencias = 0
                return
            self.alunos = session.exec(
                select(User).where(
                    User.id.in_(aluno_ids),
                    User.role == Role.ALUNO,
                    User.is_active == True,
                )
            ).all()
            self.total_alunos = len(self.alunos)

            progressos = session.exec(
                select(Progress).where(Progress.user_id.in_(aluno_ids))
            ).all()
            self.media_progresso = (
                round(sum(p.score for p in progressos) / len(progressos), 1)
                if progressos
                else 0.0
            )

            pendentes = session.exec(
                select(StudyAssignment).where(
                    StudyAssignment.user_id.in_(aluno_ids),
                    StudyAssignment.completed == False,
                )
            ).all()
            self.pendencias = len(pendentes)

    def load_studies(self):
        with rx.session() as session:
            self.studies = session.exec(
                select(Study).where(Study.is_active == True)
            ).all()
            self.study_options = [f"{s.id}:{s.title}" for s in self.studies]

    def toggle_aluno_selection(self, aluno_id: int):
        if aluno_id in self.selected_aluno_ids:
            self.selected_aluno_ids = [
                i for i in self.selected_aluno_ids if i != aluno_id
            ]
        else:
            self.selected_aluno_ids = self.selected_aluno_ids + [aluno_id]

    def assign_study(self):
        if not self.selected_study_option or not self.selected_aluno_ids:
            self.message = "Selecione um estudo e ao menos um aluno"
            self.message_type = "error"
            return
        try:
            study_id = int(self.selected_study_option.split(":")[0])
        except (ValueError, IndexError):
            self.message = "Selecione um estudo valido"
            self.message_type = "error"
            return
        with rx.session() as session:
            version = StudyService.get_latest_version(study_id)
            if not version:
                self.message = "Nenhuma versao disponivel para este estudo"
                self.message_type = "error"
                return
            for aluno_id in self.selected_aluno_ids:
                existing = session.exec(
                    select(StudyAssignment).where(
                        StudyAssignment.user_id == aluno_id,
                        StudyAssignment.study_id == study_id,
                        StudyAssignment.study_version_id == version.id,
                    )
                ).first()
                if existing:
                    continue
                assignment = StudyAssignment(
                    user_id=aluno_id,
                    study_id=study_id,
                    study_version_id=version.id,
                    assigned_by=self.current_user_id,
                )
                session.add(assignment)
            session.commit()
            self.message = "Estudo atribuido com sucesso"
            self.message_type = "success"
            self.load_alunos()
