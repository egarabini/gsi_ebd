import reflex as rx

from ..models.user import Role


def require_role(*roles: Role):
    def decorator(fn):
        async def wrapper(self, *args, **kwargs):
            if self.current_user_role not in roles:
                return rx.redirect("/login")
            result = fn(self, *args, **kwargs)
            return await result if hasattr(result, "__await__") else result
        return wrapper
    return decorator


def can_manage(target_role: int, actor_role: int) -> bool:
    """
    Retorna True se actor_role tem permissão de gerenciar target_role.
    Hierarquia: ADMIN(1) > GESTOR(2) > COORDENADOR(3) > ALUNO(4)
    """
    hierarchy = {Role.ADMIN: 0, Role.GESTOR: 1, Role.COORDENADOR: 2, Role.ALUNO: 3}
    return hierarchy.get(actor_role, 99) < hierarchy.get(target_role, 99)
