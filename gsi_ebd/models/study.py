from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class StudyLevel(str, Enum):
    BASICO = "basico"
    MEDIO = "medio"
    AVANCADO = "avancado"
    MASTER = "master"


class StudyStatus(str, Enum):
    RASCUNHO = "rascunho"       # Gestor ainda escrevendo
    PROPOSTO = "proposto"       # Gestor enviou para o Admin avaliar
    EM_REVISAO = "em_revisao"   # Admin está avaliando
    APROVADO = "aprovado"       # Admin aprovou → disponível para atribuição
    REJEITADO = "rejeitado"     # Admin rejeitou (com feedback)
    ARQUIVADO = "arquivado"     # Fora de circulação


class Study(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str = Field(default="")
    category: str = Field(default="geral")

    # --- Nível e Status ---
    level: str = Field(default="basico")            # basico|medio|avancado|master
    status: str = Field(default="rascunho")          # rascunho|proposto|em_revisao|aprovado|rejeitado|arquivado

    # --- Fluxo de Aprovação ---
    proposto_por: Optional[int] = Field(default=None)   # FK → User (Gestor)
    aprovado_por: Optional[int] = Field(default=None)   # FK → User (Admin)
    feedback_admin: str = Field(default="")             # comentário do Admin na avaliação
    approved_at: Optional[datetime] = Field(default=None)

    # --- Progressão ---
    prerequisite_study_id: Optional[int] = Field(default=None, foreign_key="study.id")

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    versions: list["StudyVersion"] = Relationship(back_populates="study")
    assignments: list["StudyAssignment"] = Relationship(back_populates="study")


class StudyVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    study_id: int = Field(foreign_key="study.id")
    version: int = Field(default=1)
    content_md: str = Field(default="")
    questions_json: str = Field(default="[]")
    available_from: Optional[datetime] = Field(default=None)
    available_until: Optional[datetime] = Field(default=None)
    target_audience: str = Field(default="all")
    created_at: Optional[datetime] = Field(default=None)

    study: Optional[Study] = Relationship(back_populates="versions")
    assignments: list["StudyAssignment"] = Relationship(back_populates="study_version")


class StudyAssignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    study_id: int = Field(foreign_key="study.id")
    study_version_id: int = Field(foreign_key="studyversion.id")
    assigned_by: int = Field(default=0)
    due_date: Optional[datetime] = Field(default=None)
    completed: bool = Field(default=False)
    created_at: Optional[datetime] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="assignments")
    study: Optional[Study] = Relationship(back_populates="assignments")
    study_version: Optional[StudyVersion] = Relationship(back_populates="assignments")


from .user import User
