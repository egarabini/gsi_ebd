import reflex as rx

from ..models.user import Role, UserStatus


class AuthService:
    @staticmethod
    def can_access_role(current_role: int, allowed_roles: tuple) -> bool:
        return current_role in allowed_roles

    @staticmethod
    def redirect_for_role(current_role: int) -> str:
        role_paths = {
            Role.ADMIN: "/admin",
            Role.GESTOR: "/gestor",
            Role.SUPERVISOR: "/supervisor",
            Role.ALUNO: "/aluno",
        }
        return role_paths.get(current_role, "/login")

    @staticmethod
    def require_login(is_authenticated: bool):
        if not is_authenticated:
            return rx.redirect("/login")
        return None

    @staticmethod
    def status_label(status: str) -> str:
        """Retorna label legível para exibição no painel."""
        labels = {
            UserStatus.ATIVO: "Ativo",
            UserStatus.SUSPENSO: "Suspenso",
            UserStatus.INATIVO: "Inativo",
            UserStatus.CANCELADO: "Cancelado",
        }
        return labels.get(status, status.capitalize())

    @staticmethod
    def status_color(status: str) -> str:
        """Retorna cor Radix para badge de status."""
        colors = {
            UserStatus.ATIVO: "green",
            UserStatus.SUSPENSO: "orange",
            UserStatus.INATIVO: "gray",
            UserStatus.CANCELADO: "red",
        }
        return colors.get(status, "gray")
