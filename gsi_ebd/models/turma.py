from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Ambiente(SQLModel, table=True):
    """Ambiente (tenant) de um Coordenador.

    Cada Coordenador tem o seu espaco isolado: instrutores, alunos, turmas,
    estudos escolhidos do catalogo e identidade visual propria. E a fronteira
    de isolamento do multi-tenant.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(default="")
    slug: str = Field(default="", index=True)

    # --- Dono do ambiente ---
    coordenador_id: int = Field(foreign_key="user.id", index=True)

    # --- Identidade visual (customizacao pelo coordenador) ---
    logo_url: str = Field(default="")
    cor_primaria: str = Field(default="#7c3aed")
    cor_secundaria: str = Field(default="#4f46e5")
    tipografia: str = Field(default="Inter")
    landing_titulo: str = Field(default="")
    landing_subtitulo: str = Field(default="")
    landing_ativa: bool = Field(default=False)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class AmbienteEstudo(SQLModel, table=True):
    """Estudo do catalogo ESCOLHIDO por um ambiente.

    O catalogo (Study/StudyVersion) e criado e mantido pelo Administrador.
    O Coordenador nao cria estudo: ele escolhe quais usar no seu ambiente.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    ambiente_id: int = Field(foreign_key="ambiente.id", index=True)
    study_id: int = Field(foreign_key="study.id", index=True)

    escolhido_por: Optional[int] = Field(default=None, foreign_key="user.id")
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class Equipe(SQLModel, table=True):
    """Equipe de instrutores, criada pelo Coordenador dentro do seu ambiente.

    Fica ENTRE o Coordenador e o Instrutor: serve para o coordenador separar os
    instrutores por NIVEL DE ESTUDO (ex.: "Equipe Basico", "Equipe Avancado"),
    e cada instrutor acompanha os alunos daquele nivel.

    Hierarquia: Administrador > Coordenador > EQUIPE > Instrutor > Aluno.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(default="")
    descricao: str = Field(default="")

    ambiente_id: Optional[int] = Field(default=None, foreign_key="ambiente.id", index=True)
    coordenador_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    nivel: str = Field(default="basico")

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class EquipeInstrutor(SQLModel, table=True):
    """Vinculo instrutor <-> equipe (um instrutor pode atuar em mais de uma)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    equipe_id: int = Field(foreign_key="equipe.id", index=True)
    instrutor_id: int = Field(foreign_key="user.id", index=True)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class Turma(SQLModel, table=True):
    """Agrupamento de alunos conduzido por um INSTRUTOR, dentro de um ambiente.

    Hierarquia: Administrador -> Coordenador -> Instrutor -> Aluno.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    descricao: str = Field(default="")

    # --- Hierarquia ---
    ambiente_id: Optional[int] = Field(default=None, foreign_key="ambiente.id", index=True)
    equipe_id: Optional[int] = Field(default=None, foreign_key="equipe.id", index=True)
    instrutor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    coordenador_id: Optional[int] = Field(default=None, foreign_key="user.id")

    # --- Plano de estudo associado (opcional) ---
    study_id: Optional[int] = Field(default=None, foreign_key="study.id")

    # --- Vigencias ---
    data_inicio: Optional[date] = Field(default=None)
    data_fim: Optional[date] = Field(default=None)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)

    membros: list["TurmaMembro"] = Relationship(back_populates="turma")


class TurmaMembro(SQLModel, table=True):
    """Vinculo aluno <-> turma, com historico."""

    id: Optional[int] = Field(default=None, primary_key=True)
    turma_id: int = Field(foreign_key="turma.id")
    user_id: int = Field(foreign_key="user.id")

    data_entrada: Optional[date] = Field(default=None)
    data_saida: Optional[date] = Field(default=None)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)

    turma: Optional[Turma] = Relationship(back_populates="membros")
