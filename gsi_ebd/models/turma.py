from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Turma(SQLModel, table=True):
    """Agrupamento de alunos sob responsabilidade de um Coordenador, dentro
    da equipe de um Gestor. Substitui o vínculo fixo e único que hoje existe
    via `User.coordenador_id`, permitindo histórico e múltiplas turmas."""

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    descricao: str = Field(default="")

    # --- Hierarquia ---
    gestor_id: int = Field(foreign_key="user.id")               # dono da turma
    coordenador_id: Optional[int] = Field(default=None, foreign_key="user.id")  # responsável operacional

    # --- Plano de estudo associado (opcional) ---
    study_id: Optional[int] = Field(default=None, foreign_key="study.id")

    # --- Vigência ---
    data_inicio: Optional[date] = Field(default=None)
    data_fim: Optional[date] = Field(default=None)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)

    membros: list["TurmaMembro"] = Relationship(back_populates="turma")


class TurmaMembro(SQLModel, table=True):
    """Vínculo aluno <-> turma, com histórico (permite reingresso e
    participação em mais de uma turma ao longo do tempo)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    turma_id: int = Field(foreign_key="turma.id")
    user_id: int = Field(foreign_key="user.id")   # aluno

    data_entrada: Optional[date] = Field(default=None)
    data_saida: Optional[date] = Field(default=None)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)

    turma: Optional[Turma] = Relationship(back_populates="membros")
