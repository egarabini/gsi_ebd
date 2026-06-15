from datetime import datetime
from enum import IntEnum
from typing import Optional

import reflex as rx
from sqlmodel import Field, Relationship


class Role(IntEnum):
    ADMIN = 1
    SUPERVISOR = 2
    GESTOR = 3
    ALUNO = 4


class User(rx.Model, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str = Field(exclude=True)
    nome: str
    role: int = Field(default=Role.ALUNO)
    gestor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    assignments: list["StudyAssignment"] = Relationship(back_populates="user")
    responses: list["UserResponse"] = Relationship(back_populates="user")
    progress_records: list["Progress"] = Relationship(back_populates="user")
