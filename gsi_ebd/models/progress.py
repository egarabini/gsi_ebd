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
    question_key: str = Field(index=True)
    question_type: int
    answer: str
    is_correct: Optional[bool] = Field(default=None)
    ai_feedback: str = Field(default="")
    time_spent_seconds: int = Field(default=0)
    created_at: Optional[datetime] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="responses")


class Progress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    study_id: int = Field(foreign_key="study.id")
    score: float = Field(default=0.0)
    total_questions: int = Field(default=0)
    correct_answers: int = Field(default=0)
    streak: int = Field(default=0)
    difficulties_json: str = Field(default="{}")
    last_activity: Optional[datetime] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="progress_records")


from .user import User
