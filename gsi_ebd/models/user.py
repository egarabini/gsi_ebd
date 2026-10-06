from datetime import date, datetime
from enum import IntEnum, Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Role(IntEnum):
    ADMIN = 1
    GESTOR = 2
    COORDENADOR = 3
    ALUNO = 4


class UserStatus(str, Enum):
    """
    Ciclo de vida do usuário na plataforma:

    ATIVO     → acesso liberado a todos os recursos
    SUSPENSO  → sem acesso até confirmar via email
                Causas: criação de conta, 1ª senha, troca de senha,
                         N tentativas de login com senha errada, reativação manual
    INATIVO   → inatividade prolongada sem acesso;
                ao tentar acessar, é avisado e pode confirmar interesse por email
    CANCELADO → acesso definitivamente bloqueado;
                reativação apenas por pedido expresso ao Gestor/Admin
    """
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    INATIVO = "inativo"
    CANCELADO = "cancelado"


class Sexo(str, Enum):
    MASCULINO = "M"
    FEMININO = "F"
    OUTRO = "O"


class Escolaridade(str, Enum):
    FUNDAMENTAL = "fundamental"
    MEDIO = "medio"
    SUPERIOR = "superior"
    POS_GRADUACAO = "pos_graduacao"


class User(SQLModel, table=True):
    # --- Chave Primária ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Identidade ---
    nome_completo: str = Field(default="")
    nome_base: str = Field(default="")          # apelido / como prefere ser chamado
    cpf: str = Field(default="", index=True)    # "000.000.000-00"
    data_nascimento: Optional[date] = Field(default=None)
    sexo: str = Field(default="")               # "M" | "F" | "O"

    # --- Fé e Perfil ---
    profissao_fe: str = Field(default="")       # denominação / igreja
    auto_descricao: str = Field(default="")     # texto livre
    escolaridade: str = Field(default="")       # fundamental|medio|superior|pos_graduacao

    # --- Endereço (preenchido via ViaCEP) ---
    cep: str = Field(default="")
    logradouro: str = Field(default="")
    numero: str = Field(default="")
    complemento: str = Field(default="")
    bairro: str = Field(default="")
    cidade: str = Field(default="")
    estado: str = Field(default="")

    # --- Contato ---
    email: str = Field(unique=True, index=True)
    telefone: str = Field(default="")

    # --- Acesso / Senha ---
    password_hash: str = Field(default="", exclude=True)
    must_change_password: bool = Field(default=True)    # força troca no 1º acesso e após reset

    # --- Status do Usuário (substitui is_active) ---
    status: str = Field(default="suspenso")             # novo usuário começa SUSPENSO
    status_reason: str = Field(default="")              # motivo do status atual
    suspension_token: str = Field(default="")           # token UUID para confirmação por email
    suspension_token_expires: Optional[datetime] = Field(default=None)

    # --- Segurança de login ---
    failed_login_attempts: int = Field(default=0)       # contagem consecutiva de falhas
    last_login_at: Optional[datetime] = Field(default=None)
    last_activity_at: Optional[datetime] = Field(default=None)  # para detectar inatividade

    # --- Hierarquia (RBAC) ---
    # ADMIN:      sem gestor_id nem coordenador_id
    # GESTOR:     sem gestor_id nem coordenador_id (criado pelo Admin)
    # COORDENADOR: gestor_id = ID do Gestor ao qual pertence
    # ALUNO:      coordenador_id = ID do Coordenador ao qual pertence
    role: int = Field(default=Role.ALUNO)
    gestor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    coordenador_id: Optional[int] = Field(default=None, foreign_key="user.id")

    # --- Metas (não limites rígidos — tracking de desempenho) ---
    meta_coordenadores: int = Field(default=0)   # meta do Gestor
    meta_alunos: int = Field(default=0)         # meta do Coordenador

    # --- Financeiro ---
    assinatura_ativa: bool = Field(default=False)
    data_vencimento: Optional[date] = Field(default=None)

    # --- Timestamps ---
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # --- Relationships ---
    assignments: list["StudyAssignment"] = Relationship(back_populates="user")
    responses: list["UserResponse"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[UserResponse.user_id]"},
    )
    progress_records: list["Progress"] = Relationship(back_populates="user")

    # --- Helpers de conveniência ---
    @property
    def is_active(self) -> bool:
        """Compatibilidade retroativa — True somente se ATIVO."""
        return self.status == UserStatus.ATIVO

    @property
    def can_access(self) -> bool:
        """Determina se o usuário pode fazer login."""
        return self.status == UserStatus.ATIVO
