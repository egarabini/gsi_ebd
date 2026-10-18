import reflex as rx

from ..models.user import Role, UserStatus


class AuthService:
    @staticmethod
    def can_access_role(current_role: int, allowed_roles: tuple) -> bool:
        return current_role in allowed_roles

    @staticmethod
    def redirect_for_role(current_role: int) -> str:
        # FONTE UNICA: utils/rbac.py (DEM-202610-002). Antes havia duas tabelas
        # iguais em arquivos diferentes - duas verdades para a mesma pergunta,
        # que divergiriam na primeira DEM que mudasse a casa de um papel.
        from ..utils.rbac import home_do_papel

        return home_do_papel(current_role)

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
