from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class NotificationType(str, Enum):
    # Financeiro
    ASSINATURA_VENCENDO = "assinatura_vencendo"   # X dias antes do vencimento
    ASSINATURA_VENCIDA = "assinatura_vencida"
    PAGAMENTO_CONFIRMADO = "pagamento_confirmado"

    # Leads (Admin)
    NOVO_LEAD = "novo_lead"                       # novo formulário de interesse

    # Estudos
    ESTUDO_PROPOSTO = "estudo_proposto"           # Gestor propôs → Admin
    ESTUDO_APROVADO = "estudo_aprovado"           # Admin aprovou → Gestor
    ESTUDO_REJEITADO = "estudo_rejeitado"         # Admin rejeitou → Gestor
    ESTUDO_ATRIBUIDO = "estudo_atribuido"         # Coordenador atribuiu → Aluno

    # Sistema
    SENHA_REDEFINIDA = "senha_redefinida"
    BOAS_VINDAS = "boas_vindas"
    GERAL = "geral"


class Notification(SQLModel, table=True):
    """Notificações in-app (sino no navbar) + gatilho para envio de email."""
    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id", index=True)   # destinatário
    tipo: str = Field(default=NotificationType.GERAL)
    titulo: str
    mensagem: str
    link: str = Field(default="")        # rota de destino ao clicar

    is_read: bool = Field(default=False)
    email_enviado: bool = Field(default=False)  # controle de envio de email

    created_at: Optional[datetime] = Field(default=None)
    read_at: Optional[datetime] = Field(default=None)
