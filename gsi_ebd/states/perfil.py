"""
PerfilState — gerencia troca de senha (obrigatória e voluntária).

Regras:
- Ao fazer login com must_change_password=True, o usuário é redirecionado aqui.
- A nova senha deve ter no mínimo 8 caracteres.
- Admin: troca aplicada diretamente (sem suspensão).
- Outros usuários: troca via UserStatusService (suspende + confirma por email).
"""
import bcrypt

from sqlmodel import select
import reflex as rx

from ..models.user import User
from ..services.user_status_service import UserStatusService
from .auth import AuthState


class PerfilState(AuthState):
    # Formulário de troca de senha
    senha_atual: str = ""
    nova_senha: str = ""
    confirma_senha: str = ""

    # Feedback
    perfil_error: str = ""
    perfil_success: str = ""
    is_loading: bool = False

    @rx.var
    def senha_fraca(self) -> bool:
        return len(self.nova_senha) > 0 and len(self.nova_senha) < 8

    @rx.var
    def senhas_divergem(self) -> bool:
        return (
            len(self.confirma_senha) > 0
            and self.nova_senha != self.confirma_senha
        )

    @rx.var
    def pode_salvar(self) -> bool:
        return (
            len(self.senha_atual) > 0
            and len(self.nova_senha) >= 8
            and self.nova_senha == self.confirma_senha
        )

    def check_perfil_auth(self):
        """Guard: redireciona para login se não autenticado."""
        if not self.is_authenticated:
            return rx.redirect("/login")

    def alterar_senha(self):
        """Processa a troca de senha."""
        self.perfil_error = ""
        self.perfil_success = ""

        if not self.pode_salvar:
            if not self.senha_atual:
                self.perfil_error = "Informe a senha atual."
            elif len(self.nova_senha) < 8:
                self.perfil_error = "A nova senha deve ter ao menos 8 caracteres."
            elif self.nova_senha != self.confirma_senha:
                self.perfil_error = "As senhas não coincidem."
            return

        self.is_loading = True

        with rx.session() as session:
            user = session.exec(
                select(User).where(User.id == self.current_user_id)
            ).first()

            if not user:
                self.perfil_error = "Usuário não encontrado. Faça login novamente."
                self.is_loading = False
                return

            # Valida senha atual
            if not bcrypt.checkpw(
                self.senha_atual.encode(), user.password_hash.encode()
            ):
                self.perfil_error = "Senha atual incorreta."
                self.is_loading = False
                return

            # Impede reutilização da senha atual
            if bcrypt.checkpw(self.nova_senha.encode(), user.password_hash.encode()):
                self.perfil_error = "A nova senha não pode ser igual à senha atual."
                self.is_loading = False
                return

            # Aplica nova senha
            user.password_hash = bcrypt.hashpw(
                self.nova_senha.encode(), bcrypt.gensalt()
            ).decode()
            user.must_change_password = False
            session.add(user)

            # Dispara fluxo de status (Admin é tratado diferente)
            UserStatusService.on_password_changed(session, user)
            session.commit()

        # Atualiza state local
        self.must_change_password = False
        self.senha_atual = ""
        self.nova_senha = ""
        self.confirma_senha = ""
        self.is_loading = False
        self.perfil_success = "Senha alterada com sucesso!"

        # Redireciona para o dashboard após troca bem-sucedida
        return rx.redirect(self.redirect_path)
