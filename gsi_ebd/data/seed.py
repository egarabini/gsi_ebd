import json
from pathlib import Path

import reflex as rx
from sqlmodel import select

from ..models import User, Role, Study, StudyVersion, StudyAssignment, UserResponse, Progress
import bcrypt


LESSONS_DIR = Path(__file__).parent / "lessons"


def seed_admin():
    with rx.session() as session:
        existing = session.exec(
            select(User).where(User.email == "admin@gsi.ebd")
        ).first()
        if not existing:
            admin = User(
                email="admin@gsi.ebd",
                password_hash=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
                nome="Administrador",
                role=Role.ADMIN,
            )
            session.add(admin)
            session.commit()


def seed_lessons():
    with rx.session() as session:
        for lesson_file in LESSONS_DIR.glob("*.json"):
            data = json.loads(lesson_file.read_text(encoding="utf-8"))
            existing = session.exec(
                select(Study).where(Study.title == data["title"])
            ).first()
            if not existing:
                study = Study(
                    title=data["title"],
                    description=data.get("description", ""),
                    category=data.get("category", "geral"),
                )
                session.add(study)
                session.commit()
                session.refresh(study)
                questions_json = json.dumps(data.get("questions", []), ensure_ascii=False)
                version = StudyVersion(
                    study_id=study.id,
                    version=1,
                    content_md=data.get("content_md", ""),
                    questions_json=questions_json,
                )
                session.add(version)
                session.commit()


def seed_all():
    seed_admin()
    seed_lessons()


if __name__ == "__main__":
    seed_all()
    print("Seed concluido com sucesso!")
