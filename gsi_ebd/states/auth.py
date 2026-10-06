from typing import Optional

from sqlmodel import select
import reflex as rx
import bcrypt

from ..models.user import User, Role, UserStatus
from ..services.auth_service import AuthService
from ..services.user_status_service import UserStatusService


class AuthState(rx.State):
    # --- Sessão ---
    is_authenticated: bool = False
    current_user_id: Optional[int] = None
    current_user_name: str = ""
    current_user_role: int = Role.ALUNO
    current_user_status: str = UserStatus.SUSPENSO
    current_user_ambiente: int = 0   # 0 = sem fronteira (ADMIN)

    # --- Formulário de login ---
    login_email: str = ""
    login_password: str = ""
    login_error: str = ""
    login_warning: str = ""   # avisos não-bloqueantes (ex: tentativas restantes)

    # --- Formulário de registro (desabilitado — criação via Admin/Coordenador) ---
    register_nome: str = ""
    register_email: str = ""
    register_password: str = ""
    register_error: str = ""

    # --- Flags de UI ---
    must_change_password: bool = False
    show_status_modal: bool = False   # modal para INATIVO pedindo reativação
    status_modal_email: str = ""

    # ── Vars computados por role ──────────────────────────────
    @rx.var
    def is_admin(self) -> bool:
        return self.current_user_role == Role.ADMIN

    @rx.var
    def is_instrutor(self) -> bool:
        return self.current_user_role == Role.INSTRUTOR


    @rx.var
    def is_coordenador(self) -> bool:
        return self.current_user_role == Role.COORDENADOR

    @rx.var
    def is_aluno(self) -> bool:
        return self.current_user_role == Role.ALUNO

    @rx.var
    def redirect_path(self) -> str:
        if not self.is_authenticated:
            return "/login"
        return AuthService.redirect_for_role(self.current_user_role)

    @rx.var
    def user_is_active(self) -> bool:
        return self.current_user_status == UserStatus.ATIVO

    # ── Login ────────────────────────────────────────────────
    def login(self):
        self.login_error = ""
        self.login_warning = ""

        if not self.login_email or not self.login_password:
            self.login_error = "Preencha email e senha."
            return

        with rx.session() as session:
            user = session.exec(
                select(User).where(User.email == self.login_email)
            ).first()

            # Usuário não encontrado
            if not user:
                self.login_error = "Email ou senha inválidos."
                return

            # ── REGRA: Admin nunca é bloqueado por status ───────
            is_admin = int(user.role) == Role.ADMIN
            if not is_admin:
                # Verificar status antes da senha para CANCELADO
                if user.status == UserStatus.CANCELADO:
                    self.login_error = "Acesso não permitido. Entre em contato com o administrador."
                    return

                # Verificar status INATIVO
                if user.status == UserStatus.INATIVO:
                    self.show_status_modal = True
                    self.status_modal_email = user.email
                    self.login_error = ""
                    return

                # Verificar status SUSPENSO
                if user.status == UserStatus.SUSPENSO:
                    self.login_error = (
                        "Conta suspensa. Verifique seu email para ativar o acesso. "
                        "Não recebeu? Use 'Reenviar email'."
                    )
                    return

            # Validar senha
            senha_correta = bcrypt.checkpw(
                self.login_password.encode(), user.password_hash.encode()
            )

            if not senha_correta:
                result = UserStatusService.on_login_failure(session, user)
                session.commit()
                if result["suspended"]:
                    self.login_error = (
                        "Muitas tentativas incorretas. Conta suspensa. "
                        "Verifique seu email para reativar."
                    )
                else:
                    remaining = result["attempts_left"]
                    self.login_error = f"Senha inválida. {remaining} tentativa(s) restante(s)."
                return

            # Login bem-sucedido
            UserStatusService.on_login_success(session, user)
            session.commit()

            self.is_authenticated = True
            self.current_user_id = user.id
            self.current_user_name = user.nome_base or user.nome_completo
            self.current_user_role = user.role
            self.current_user_ambiente = user.ambiente_id or 0
            self.current_user_status = user.status
            self.must_change_password = user.must_change_password
            self.login_email = ""
            self.login_password = ""

            if self.must_change_password:
                return rx.redirect("/perfil/alterar-senha")

            return rx.redirect(self.redirect_path)

    # ── Reativação de conta INATIVA ──────────────────────────
    def request_reactivation(self):
        """Usuário inativo confirmou interesse em reativar — envia email."""
        self.show_status_modal = False
        with rx.session() as session:
            user = session.exec(
                select(User).where(User.email == self.status_modal_email)
            ).first()
            if user:
                sent = UserStatusService.request_reactivation(session, user)
                session.commit()
                if sent:
                    self.login_warning = (
                        "Email de reativação enviado! Verifique sua caixa de entrada."
                    )
                else:
                    self.login_error = "Não foi possível enviar o email. Tente novamente."

    def dismiss_status_modal(self):
        self.show_status_modal = False
        self.status_modal_email = ""

    # ── Confirmação de token via URL /confirmar/{token} ──────
    def confirm_account_token(self, token: str):
        """Chamado na página /confirmar/{token}."""
        with rx.session() as session:
            success, msg = UserStatusService.confirm_token(session, user_token=token)
            session.commit()
        if success:
            self.login_warning = msg
        else:
            self.login_error = msg
        return rx.redirect("/login")

    # ── Logout ───────────────────────────────────────────────
    def logout(self):
        self.is_authenticated = False
        self.current_user_id = None
        self.current_user_ambiente = 0
        self.current_user_name = ""
        self.current_user_role = Role.ALUNO
        self.current_user_status = UserStatus.SUSPENSO
        self.login_email = ""
        self.login_password = ""
        self.login_error = ""
        self.login_warning = ""
        return rx.redirect("/login")

    # ── Guard de rota ─────────────────────────────────────────
    def check_auth(self):
        return AuthService.require_login(self.is_authenticated)
