from datetime import datetime
from typing import Optional

import reflex as rx
from sqlmodel import select

from ..models import Progress, StudyAssignment, UserResponse, QuestionType
from .escopo_service import EscopoService


class ProgressService:
    @staticmethod
    def save_response(
        user_id: int,
        study_version_id: int,
        question_key: str,
        question_type: QuestionType,
        answer: str,
        is_correct: Optional[bool],
        ai_feedback: str = "",
        time_spent_seconds: int = 0,
    ) -> None:
        ambiente_id = EscopoService.ambiente_do_usuario(user_id)
        with rx.session() as session:
            response = UserResponse(
                user_id=user_id,
                ambiente_id=ambiente_id,
                study_version_id=study_version_id,
                question_key=question_key,
                question_type=question_type,
                answer=answer,
                is_correct=is_correct,
                ai_feedback=ai_feedback,
                time_spent_seconds=time_spent_seconds,
            )
            session.add(response)
            session.commit()

    @staticmethod
    def finish_study(
        user_id: int,
        study_id: int,
        score: float,
        total_questions: int,
        correct_answers: int,
        streak: int,
    ) -> None:
        ambiente_id = EscopoService.ambiente_do_usuario(user_id)
        with rx.session() as session:
            progress = Progress(
                user_id=user_id,
                ambiente_id=ambiente_id,
                study_id=study_id,
                score=score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                streak=streak,
                last_activity=datetime.utcnow(),
            )
            session.add(progress)
            assignment = session.exec(
                select(StudyAssignment).where(
                    StudyAssignment.user_id == user_id,
                    StudyAssignment.study_id == study_id,
                )
            ).first()
            if assignment:
                assignment.completed = True
                session.add(assignment)
            session.commit()
