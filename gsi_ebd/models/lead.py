from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class LeadStatus(str, Enum):
    PENDENTE = "pendente"       # formulário recebido, aguardando avaliação
    EM_CONTATO = "em_contato"  # Admin entrou em contato
    CONVERTIDO = "convertido"  # virou Gestor na plataforma
    RECUSADO = "recusado"       # Admin decidiu não aprovar


class Lead(SQLModel, table=True):
    """Cadastro de interesse submetido via landing page."""
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Dados do interessado ---
    nome: str
    email: str = Field(index=True)
    telefone: str = Field(default="")
    cidade: str = Field(default="")
    estado: str = Field(default="")

    # --- Contexto de Fé ---
    membro_igreja: bool = Field(default=False)
    nome_igreja: str = Field(default="")
    denominacao: str = Field(default="")

    # --- Mensagem livre ---
    mensagem: str = Field(default="")

    # --- Status e controle ---
    status: str = Field(default="pendente")
    observacoes_admin: str = Field(default="")  # notas internas do Admin
    gestor_criado_id: Optional[int] = Field(default=None)  # FK → User quando convertido

    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
