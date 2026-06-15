import json
from typing import Dict, List, Optional

import reflex as rx

from ..models.study import Study, StudyVersion, StudyAssignment
from ..models.progress import UserResponse, Progress
from .auth import AuthState


class AlunoState(AuthState):
    assigned_studies: List[Dict] = []
    current_study_id: Optional[int] = None
    current_version_id: Optional[int] = None
    study_content: str = ""
    study_questions: List[Dict] = []
    current_question_idx: int = 0
    user_answer: str = ""
    answer_feedback: str = ""
    show_feedback: bool = False
    score: float = 0.0
    total_answered: int = 0
    correct_count: int = 0
    streak: int = 0
    ai_context: str = ""

    def load_assigned_studies(self):
        with rx.session() as session:
            assignments = session.exec(
                StudyAssignment.select().where(
                    StudyAssignment.user_id == self.current_user_id,
                    StudyAssignment.completed == False,
                )
            ).all()
            self.assigned_studies = []
            for a in assignments:
                study = session.exec(
                    Study.select().where(Study.id == a.study_id)
                ).first()
                version = session.exec(
                    StudyVersion.select().where(StudyVersion.id == a.study_version_id)
                ).first()
                if study and version:
                    self.assigned_studies.append({
                        "assignment_id": a.id,
                        "study_id": study.id,
                        "study_title": study.title,
                        "study_category": study.category,
                        "version_id": version.id,
                        "version": version.version,
                    })

    def start_study(self, study_id: int, version_id: int):
        self.current_study_id = study_id
        self.current_version_id = version_id
        self.current_question_idx = 0
        self.user_answer = ""
        self.answer_feedback = ""
        self.show_feedback = False
        with rx.session() as session:
            version = session.exec(
                StudyVersion.select().where(StudyVersion.id == version_id)
            ).first()
            if version:
                self.study_content = version.content_md
                self.study_questions = json.loads(version.questions_json)

    def submit_answer(self):
        if not self.study_questions:
            return
        question = self.study_questions[self.current_question_idx]
        correct = question.get("answer", "")
        q_type = question.get("type", "multiple_choice")
        is_correct = False
        if q_type == "fill_blank":
            is_correct = self.user_answer.strip().lower() == correct.strip().lower()
        elif q_type == "true_false":
            is_correct = self.user_answer.strip().lower() == correct.strip().lower()
        elif q_type == "multiple_choice":
            is_correct = self.user_answer.strip() == correct.strip()
        elif q_type == "open":
            is_correct = True

        self.total_answered += 1
        if is_correct:
            self.correct_count += 1
            self.streak += 1
            self.answer_feedback = "Correto! Parabens!"
        else:
            self.streak = 0
            self.answer_feedback = f"Incorreto. A resposta correta é: {correct}"

        self.show_feedback = True
        if self.total_answered > 0:
            self.score = (self.correct_count / self.total_answered) * 100

        with rx.session() as session:
            from ..models.progress import QuestionType
            type_map = {
                "fill_blank": QuestionType.FILL_BLANK,
                "true_false": QuestionType.TRUE_FALSE,
                "multiple_choice": QuestionType.MULTIPLE_CHOICE,
                "open": QuestionType.OPEN,
            }
            response = UserResponse(
                user_id=self.current_user_id,
                study_version_id=self.current_version_id,
                question_key=question.get("key", f"q{self.current_question_idx}"),
                question_type=type_map.get(q_type, QuestionType.MULTIPLE_CHOICE),
                answer=self.user_answer,
                is_correct=is_correct,
            )
            session.add(response)
            session.commit()

    def next_question(self):
        self.show_feedback = False
        self.user_answer = ""
        if self.current_question_idx < len(self.study_questions) - 1:
            self.current_question_idx += 1
        else:
            self._finish_study()

    def _finish_study(self):
        with rx.session() as session:
            progress = Progress(
                user_id=self.current_user_id,
                study_id=self.current_study_id,
                score=self.score,
                total_questions=self.total_answered,
                correct_answers=self.correct_count,
                streak=self.streak,
            )
            session.add(progress)
            assignment = session.exec(
                StudyAssignment.select().where(
                    StudyAssignment.user_id == self.current_user_id,
                    StudyAssignment.study_id == self.current_study_id,
                )
            ).first()
            if assignment:
                assignment.completed = True
                session.add(assignment)
            session.commit()
        self.current_study_id = None
        self.current_version_id = None
