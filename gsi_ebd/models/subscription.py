from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class SubscriptionStatus(str, Enum):
    ATIVA = "ativa"
    PENDENTE = "pendente"       # aguardando pagamento
    VENCIDA = "vencida"         # passou do prazo (após carência)
    CANCELADA = "cancelada"


class PaymentMethod(str, Enum):
    SIMULADO = "simulado"       # fase inicial — sem gateway real
    PIX = "pix"
    BOLETO = "boleto"
    CARTAO = "cartao"
    MERCADO_PAGO = "mercado_pago"


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    # --- Valores ---
    valor: float = Field(default=0.0)

    # --- Status ---
    status: str = Field(default=SubscriptionStatus.PENDENTE)

    # --- Datas ---
    data_inicio: Optional[date] = Field(default=None)
    data_vencimento: Optional[date] = Field(default=None)
    data_pagamento: Optional[date] = Field(default=None)

    # --- Pagamento ---
    metodo_pagamento: str = Field(default=PaymentMethod.SIMULADO)
    referencia_externa: str = Field(default="")  # ID do MP quando integrado

    # --- Controle ---
    observacoes: str = Field(default="")
    criado_por: int = Field(default=0)           # user_id do Admin que criou

    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class PaymentHistory(SQLModel, table=True):
    """Histórico de todos os pagamentos registrados."""
    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(foreign_key="subscription.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    valor_pago: float
    data_pagamento: date
    metodo: str = Field(default=PaymentMethod.SIMULADO)
    referencia: str = Field(default="")          # código / comprovante

    registrado_por: int = Field(default=0)       # user_id do Admin
    observacoes: str = Field(default="")

    created_at: Optional[datetime] = Field(default=None)
