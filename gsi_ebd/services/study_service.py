import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import reflex as rx
from sqlmodel import select

from ..models import Study, StudyVersion, StudyAssignment, User, Role


@dataclass
class StudySnapshot:
    assignment_id: int
    study_id: int
    study_title: str
    study_category: str
    version_id: int
    version: int
    version_label: str


class StudyService:
    @staticmethod
    def list_assigned_studies(user_id: int) -> List[StudySnapshot]:
        with rx.session() as session:
            assignments = session.exec(
                select(StudyAssignment).where(
                    StudyAssignment.user_id == user_id,
                    StudyAssignment.completed == False,
                )
            ).all()

            snapshots: List[StudySnapshot] = []
            for assignment in assignments:
                study = session.exec(
                    select(Study).where(Study.id == assignment.study_id)
                ).first()
                version = session.exec(
                    select(StudyVersion).where(StudyVersion.id == assignment.study_version_id)
                ).first()
                if study and version:
                    snapshots.append(
                        StudySnapshot(
                            assignment_id=assignment.id,
                            study_id=study.id,
                            study_title=study.title,
                            study_category=study.category,
                            version_id=version.id,
                            version=version.version,
                            version_label=f"Versao {version.version}",
                        )
                    )
            return snapshots

    @staticmethod
    def get_latest_version(study_id: int) -> Optional[StudyVersion]:
        with rx.session() as session:
            return session.exec(
                select(StudyVersion)
                .where(StudyVersion.study_id == study_id)
                .order_by(StudyVersion.version.desc())
            ).first()

    @staticmethod
    def load_version_payload(version_id: int) -> Dict[str, Any]:
        with rx.session() as session:
            version = session.exec(
                select(StudyVersion).where(StudyVersion.id == version_id)
            ).first()
            if not version:
                return {"content_md": "", "questions": []}
            try:
                questions = json.loads(version.questions_json or "[]")
            except json.JSONDecodeError:
                questions = []
            return {"content_md": version.content_md or "", "questions": questions}

    @staticmethod
    def is_gestor_of_user(gestor_id: Optional[int], aluno_id: int) -> bool:
        if gestor_id is None:
            return False
        with rx.session() as session:
            aluno = session.exec(select(User).where(User.id == aluno_id)).first()
            return bool(aluno and aluno.gestor_id == gestor_id)
