from datetime import datetime
from typing import Optional

import reflex as rx
from sqlmodel import Field, Relationship


class Study(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str = Field(default="")
    category: str = Field(default="geral")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    versions: list["StudyVersion"] = Relationship(back_populates="study")
    assignments: list["StudyAssignment"] = Relationship(back_populates="study")


class StudyVersion(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    study_id: int = Field(foreign_key="study.id")
    version: int = Field(default=1)
    content_md: str = Field(default="")
    questions_json: str = Field(default="[]")
    available_from: Optional[datetime] = Field(default=None)
    available_until: Optional[datetime] = Field(default=None)
    target_audience: str = Field(default="all")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    study: Optional[Study] = Relationship(back_populates="versions")
    assignments: list["StudyAssignment"] = Relationship(back_populates="study_version")


class StudyAssignment(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    study_id: int = Field(foreign_key="study.id")
    study_version_id: int = Field(foreign_key="studyversion.id")
    assigned_by: int = Field(foreign_key="user.id")
    due_date: Optional[datetime] = Field(default=None)
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="assignments")
    study: Optional[Study] = Relationship(back_populates="assignments")
    study_version: Optional[StudyVersion] = Relationship(back_populates="assignments")
