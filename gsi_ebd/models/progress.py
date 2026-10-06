from datetime import datetime
from enum import IntEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class QuestionType(IntEnum):
    FILL_BLANK = 1
    TRUE_FALSE = 2
    MULTIPLE_CHOICE = 3
    OPEN = 4


class UserResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    study_version_id: int = Field(foreign_key="studyversion.id")
    # --- Isolamento por tenant: o ambiente (coordenador) dono deste registro ---
    ambiente_id: Optional[int] = Field(default=None, foreign_key="ambiente.id", index=True)
    question_key: str = Field(index=True)
    question_type: int
    answer: str
    is_correct: Optional[bool] = Field(default=None)   # None = aguardando avaliacao
    ai_feedback: str = Field(default="")
    # --- Avaliacao humana (o "instrutor" do modelo SGI7) ---
    # Questoes abertas nascem com is_correct=None e so sao resolvidas aqui.
    instructor_feedback: str = Field(default="")
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")
    reviewed_at: Optional[datetime] = Field(default=None)
    time_spent_seconds: int = Field(default=0)
    created_at: Optional[datetime] = Field(default=None)

    # Duas FKs para user (dono da resposta e instrutor que avaliou), entao a
    # relationship precisa dizer explicitamente qual delas usar.
    user: Optional["User"] = Relationship(
        back_populates="responses",
        sa_relationship_kwargs={"foreign_keys": "[UserResponse.user_id]"},
    )


class Progress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    study_id: int = Field(foreign_key="study.id")
    # --- Isolamento por tenant: o ambiente (coordenador) dono deste registro ---
    ambiente_id: Optional[int] = Field(default=None, foreign_key="ambiente.id", index=True)
    score: float = Field(default=0.0)
    total_questions: int = Field(default=0)
    correct_answers: int = Field(default=0)
    streak: int = Field(default=0)
    difficulties_json: str = Field(default="{}")
    last_activity: Optional[datetime] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="progress_records")


from .user import User
