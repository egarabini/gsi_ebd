from ..models.user import Role


def require_role(*roles: Role):
    def decorator(fn):
        async def wrapper(self, *args, **kwargs):
            if self.current_user_role not in roles:
                return rx.redirect("/login")
            return await fn(self, *args, **kwargs) if hasattr(fn, '__self__') else fn(self, *args, **kwargs)
        return wrapper
    return decorator


def can_manage(target_role: int, actor_role: int) -> bool:
    hierarchy = {Role.ADMIN: 0, Role.SUPERVISOR: 1, Role.GESTOR: 2, Role.ALUNO: 3}
    return hierarchy.get(actor_role, 99) < hierarchy.get(target_role, 99)
