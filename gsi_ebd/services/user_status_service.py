"""
UserStatusService — gerencia o ciclo de vida do status do usuário.

Regras:
    ATIVO     → acesso pleno
    SUSPENSO  → gerado automaticamente; acesso bloqueado até confirmar via email
    INATIVO   → detectado por ausência de atividade; ao tentar acessar,
                usuário é avisado e pode pedir reativação por email
    CANCELADO → acesso definitivamente bloqueado; só Admin/Gestor reativa
"""
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from ..models.user import User, UserStatus
from ..models.notification import Notification, NotificationType
from .email_service import (
    send_confirmacao_conta,
    send_troca_senha,
    send_conta_suspensa_tentativas,
    send_reativacao_inativo,
    send_conta_cancelada,
)

# Número de tentativas de login antes de suspender a conta
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))

# Horas de validade do token de confirmação
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

# Dias de inatividade antes de tornar INATIVO
INACTIVITY_DAYS = int(os.getenv("INACTIVITY_DAYS", "60"))


def _generate_token() -> str:
    return str(uuid.uuid4()).replace("-", "")


def _create_suspension_token(user: User) -> str:
    """Gera token de confirmação e salva no usuário."""
    token = _generate_token()
    user.suspension_token = token
    user.suspension_token_expires = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return token


def _notify_inapp(session: Session, user_id: int, tipo: str, titulo: str, mensagem: str, link: str = ""):
    """Cria notificação in-app (sino no navbar)."""
    notification = Notification(
        user_id=user_id,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link,
    )
    session.add(notification)


class UserStatusService:
    """
    Gerencia todas as transições de status do usuário e dispara
    notificações in-app + emails correspondentes.

    REGRA FUNDAMENTAL: O usuário com role ADMIN (role == 1) NUNCA pode
    ser suspenso, inativado ou cancelado por nenhuma lógica automática
    ou manual. Ele é permanentemente ATIVO.
    """

    @staticmethod
    def _is_protected_admin(user: User) -> bool:
        """Retorna True se o usuário é Admin e não pode ter o status alterado."""
        from ..models.user import Role
        return int(user.role) == Role.ADMIN

    # ─────────────────────────────────────────────
    # Criação de usuário → começa SUSPENSO
    # ─────────────────────────────────────────────
    @staticmethod
    def on_user_created(session: Session, user: User):
        """
        Chamado ao criar um novo usuário.
        Status inicial: SUSPENSO (aguarda confirmação por email).
        Admin é sempre criado como ATIVO — nunca é suspenso.
        """
        # Admin é protegido: sempre ATIVO, nunca precisa de confirmação
        if UserStatusService._is_protected_admin(user):
            user.status = UserStatus.ATIVO
            user.status_reason = "Administrador do sistema — sempre ativo"
            session.add(user)
            return

        token = _create_suspension_token(user)
        user.status = UserStatus.SUSPENSO
        user.status_reason = "Conta recém-criada — aguardando confirmação por email"
        session.add(user)

        send_confirmacao_conta(
            nome=user.nome_base or user.nome_completo,
            email=user.email,
            token=token,
        )

        _notify_inapp(
            session, user.id,
            NotificationType.BOAS_VINDAS,
            "Bem-vindo ao Didasko!",
            "Sua conta foi criada. Verifique seu email para ativar o acesso.",
        )

    # ─────────────────────────────────────────────
    # Confirmação via token (email)
    # ─────────────────────────────────────────────
    @staticmethod
    def confirm_token(session: Session, token: str) -> tuple[bool, str]:
        """
        Valida token de suspensão e ativa a conta.
        Retorna (success: bool, mensagem: str).
        """
        user = session.exec(
            select(User).where(User.suspension_token == token)
        ).first()

        if not user:
            return False, "Token inválido ou já utilizado."

        if not user.suspension_token_expires or datetime.utcnow() > user.suspension_token_expires:
            return False, "Token expirado. Solicite um novo link."

        if user.status == UserStatus.CANCELADO:
            return False, "Conta cancelada. Entre em contato com o administrador."

        # Ativa a conta
        user.status = UserStatus.ATIVO
        user.status_reason = "Confirmado por email"
        user.suspension_token = ""
        user.suspension_token_expires = None
        user.failed_login_attempts = 0
        user.must_change_password = (user.last_login_at is None)  # força troca apenas no 1º login
        session.add(user)

        _notify_inapp(
            session, user.id,
            NotificationType.GERAL,
            "Conta ativada!",
            "Seu acesso foi confirmado com sucesso. Bem-vindo!",
            link="/login",
        )

        return True, "Conta ativada com sucesso! Faça login."

    # ─────────────────────────────────────────────
    # Login — gerencia tentativas e status
    # ─────────────────────────────────────────────
    @staticmethod
    def on_login_success(session: Session, user: User):
        """Atualiza metadados após login bem-sucedido."""
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.last_activity_at = datetime.utcnow()
        session.add(user)

    @staticmethod
    def on_login_failure(session: Session, user: User) -> dict:
        """
        Registra tentativa falha. Se atingir MAX_FAILED_LOGIN_ATTEMPTS,
        suspende a conta e envia email.
        Admin NUNCA é suspenso por tentativas de login.
        Retorna {"suspended": bool, "attempts_left": int}
        """
        # Admin é imune a suspensão por tentativas de login
        if UserStatusService._is_protected_admin(user):
            user.failed_login_attempts += 1
            session.add(user)
            return {"suspended": False, "attempts_left": MAX_FAILED_LOGIN_ATTEMPTS}

        user.failed_login_attempts += 1
        attempts_left = MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts

        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            token = _create_suspension_token(user)
            user.status = UserStatus.SUSPENSO
            user.status_reason = f"Suspensa por {MAX_FAILED_LOGIN_ATTEMPTS} tentativas de login com senha incorreta"
            session.add(user)

            send_conta_suspensa_tentativas(
                nome=user.nome_base or user.nome_completo,
                email=user.email,
                token=token,
            )

            _notify_inapp(
                session, user.id,
                NotificationType.GERAL,
                "Conta suspensa por segurança",
                "Muitas tentativas de login. Verifique seu email para reativar.",
            )
            return {"suspended": True, "attempts_left": 0}

        session.add(user)
        return {"suspended": False, "attempts_left": max(0, attempts_left)}

    # ─────────────────────────────────────────────
    # Troca de senha → suspende temporariamente
    # ─────────────────────────────────────────────
    @staticmethod
    def on_password_changed(session: Session, user: User):
        """
        Ao trocar senha, suspende a conta e exige confirmação por email.
        Isso garante que alterações não autorizadas sejam detectadas.
        Admin NUNCA é suspenso — troca de senha é aplicada diretamente.
        """
        # Admin: aplica a troca sem suspensão nem email de confirmação
        if UserStatusService._is_protected_admin(user):
            user.status = UserStatus.ATIVO
            user.must_change_password = False
            session.add(user)
            return

        token = _create_suspension_token(user)
        user.status = UserStatus.SUSPENSO
        user.status_reason = "Senha alterada — aguardando confirmação por email"
        session.add(user)

        send_troca_senha(
            nome=user.nome_base or user.nome_completo,
            email=user.email,
            token=token,
        )

        _notify_inapp(
            session, user.id,
            NotificationType.SENHA_REDEFINIDA,
            "Senha alterada",
            "Verifique seu email para confirmar a alteração e reativar seu acesso.",
        )

    # ─────────────────────────────────────────────
    # Usuário INATIVO tenta acessar → pede reativação
    # ─────────────────────────────────────────────
    @staticmethod
    def request_reactivation(session: Session, user: User) -> bool:
        """
        Usuário INATIVO solicita reativação.
        Gera token e envia email com link de confirmação.
        Retorna True se email enviado.
        """
        if user.status != UserStatus.INATIVO:
            return False

        token = _create_suspension_token(user)
        user.status_reason = "Reativação solicitada — aguardando confirmação por email"
        session.add(user)

        return send_reativacao_inativo(
            nome=user.nome_base or user.nome_completo,
            email=user.email,
            token=token,
        )

    # ─────────────────────────────────────────────
    # Admin/Gestor cancela conta
    # ─────────────────────────────────────────────
    @staticmethod
    def cancel_user(session: Session, user: User, reason: str = "", cancelled_by: int = 0):
        """
        Cancela definitivamente o acesso do usuário.
        Somente Admin/Gestor pode fazer isso.
        Admin NUNCA pode ser cancelado.
        """
        if UserStatusService._is_protected_admin(user):
            raise ValueError("O usuário Administrador não pode ser cancelado.")

        user.status = UserStatus.CANCELADO
        user.status_reason = reason or "Conta cancelada pelo administrador"
        user.suspension_token = ""
        user.suspension_token_expires = None
        session.add(user)

        send_conta_cancelada(
            nome=user.nome_base or user.nome_completo,
            email=user.email,
        )

        _notify_inapp(
            session, user.id,
            NotificationType.GERAL,
            "Conta cancelada",
            user.status_reason,
        )

    # ─────────────────────────────────────────────
    # Detecção automática de inatividade (job)
    # ─────────────────────────────────────────────
    @staticmethod
    def mark_inactive_users(session: Session) -> int:
        """
        Marca como INATIVO todos os usuários ATIVOS que não acessam
        há mais de INACTIVITY_DAYS dias.
        Retorna o número de usuários afetados.
        """
        cutoff = datetime.utcnow() - timedelta(days=INACTIVITY_DAYS)
        users = session.exec(
            select(User).where(
                User.status == UserStatus.ATIVO,
                User.last_activity_at < cutoff,
                User.role != 1,  # REGRA: Admin (role=1) nunca é inativado automaticamente
            )
        ).all()

        count = 0
        for user in users:
            user.status = UserStatus.INATIVO
            user.status_reason = f"Sem acesso há mais de {INACTIVITY_DAYS} dias"
            session.add(user)
            count += 1

        if count:
            session.commit()

        return count

    # ─────────────────────────────────────────────
    # Reenvio de token (token expirado)
    # ─────────────────────────────────────────────
    @staticmethod
    def resend_confirmation(session: Session, email: str) -> bool:
        """
        Usuário pede reenvio do email de confirmação (token expirou).
        Gera novo token e reenvia.
        """
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or user.status not in (UserStatus.SUSPENSO, UserStatus.INATIVO):
            return False

        token = _create_suspension_token(user)
        session.add(user)
        session.commit()

        send_confirmacao_conta(
            nome=user.nome_base or user.nome_completo,
            email=user.email,
            token=token,
        )
        return True
