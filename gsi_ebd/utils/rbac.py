"""Guarda de papel do Didasko (DEM-202610-002).

Uma matriz unica (PERMISSOES) responde por ROTAS e por ACOES de evento. O cliente
do Reflex pode disparar um evento do estado direto, sem passar pela pagina: por
isso guarda de rota sozinha nao basta (achado do EVAL da DEM-001 e do AUXILIAR na
DEM-002).

Premissa de seguranca: `current_user_role` NAO tem setter automatico. O
`rxconfig.py` desliga `state_auto_setters` e os setters explicitos existem so
para campo de formulario - o cliente nao escreve a propria identidade.
"""
import functools

import reflex as rx

from ..models.user import Role

# ── matriz unica: rotas e acoes de evento ───────────────────────────────────
# Rota fora desta matriz nao tem guarda. As publicas/abertas entram com _TODOS
# para `pode` ser total (F-06): o guarda de rota checa autenticacao antes.
_TODOS = (Role.ADMIN, Role.REVISOR, Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO)

PERMISSOES: dict[str, tuple[int, ...]] = {
    # rotas publicas ou abertas a qualquer logado
    "rota:/": _TODOS,
    "rota:/login": _TODOS,
    "rota:/confirmar/[token]": _TODOS,
    "rota:/homenagens": _TODOS,
    "rota:/aluno": _TODOS,
    "rota:/aluno/licao": _TODOS,
    "rota:/aluno/pareceres": _TODOS,
    "rota:/perfil/alterar-senha": _TODOS,
    # rotas guardadas (usadas pelos handlers de on_load)
    "rota:/admin": (Role.ADMIN, Role.REVISOR),
    "rota:/coordenador": (Role.ADMIN, Role.COORDENADOR),
    "rota:/revisao": (Role.ADMIN, Role.INSTRUTOR),
    # acoes (usadas pelos eventos dos estados)
    "acao:catalogo_ler": (Role.ADMIN, Role.REVISOR),
    "acao:catalogo_aprovar": (Role.ADMIN,),
    "acao:usuarios": (Role.ADMIN,),
    "acao:leads": (Role.ADMIN,),
    "acao:coordenacao": (Role.ADMIN, Role.COORDENADOR),
    "acao:revisao": (Role.ADMIN, Role.INSTRUTOR),
}

# casa de cada papel - usada no redirect de quem nao tem a rota
HOME_DO_PAPEL: dict[int, str] = {
    Role.ADMIN: "/admin",
    Role.REVISOR: "/admin",
    Role.COORDENADOR: "/coordenador",
    Role.INSTRUTOR: "/revisao",
    Role.ALUNO: "/aluno",
}


def home_do_papel(papel: int) -> str:
    """Rota inicial do papel; desconhecido vai para o login (nunca para si mesmo)."""
    return HOME_DO_PAPEL.get(papel, "/login")


def pode(chave: str, papel: int) -> bool:
    """True se o papel pode a chave. Chave desconhecida NEGA (fecha por padrao)."""
    permitidos = PERMISSOES.get(chave)
    if not permitidos:
        return False
    return papel in permitidos


def exige(chave: str):
    """Decora um EVENTO de estado: sem papel, o corpo nao roda.

    O wrapper e SINCRONO de proposito: nenhum handler dos estados administrativos
    usa `yield` nem `async`, e o `require_role` antigo (async) converteria handler
    sincrono em assincrono sem necessidade.

    Grava `__exige__` no wrapper - o teste varre as classes e reprova evento
    publico sem marcador.
    """

    def decorador(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not pode(chave, getattr(self, "current_user_role", -1)):
                return None
            return fn(self, *args, **kwargs)

        wrapper.__exige__ = chave
        return wrapper

    return decorador


def guarda_rota(rota: str):
    """Decora um handler de `on_load`: nao logado vai ao login; sem papel, a casa."""

    def decorador(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "is_authenticated", False):
                return rx.redirect("/login")
            papel = getattr(self, "current_user_role", -1)
            if not pode("rota:" + rota, papel):
                return rx.redirect(home_do_papel(papel))
            return fn(self, *args, **kwargs)

        wrapper.__guarda_rota__ = rota
        return wrapper

    return decorador


# ── legado (mantido para nao quebrar imports; nao e guarda de evento) ────────
def require_role(*roles: Role):
    """DEPRECADO: decorator async que nunca foi usado por nenhum arquivo.

    Mantido apenas porque pode haver import em codigo antigo. Use `exige`.
    """

    def decorator(fn):
        async def wrapper(self, *args, **kwargs):
            if self.current_user_role not in roles:
                return rx.redirect("/login")
            result = fn(self, *args, **kwargs)
            return await result if hasattr(result, "__await__") else result

        return wrapper

    return decorator


def can_manage(target_role: int, actor_role: int) -> bool:
    """Hierarquia: ADMIN(1) > REVISOR(1.5) > COORDENADOR(2) > INSTRUTOR(3) > ALUNO(4).

    ATENCAO: nao confere o AMBIENTE (tenant) - ver DEM-202610-010. Nao e mais a
    guarda de nenhum evento: o `exige` barra antes.
    """
    hierarchy = {Role.ADMIN: 0, Role.REVISOR: 1, Role.COORDENADOR: 2, Role.INSTRUTOR: 3, Role.ALUNO: 4}
    return hierarchy.get(actor_role, 99) < hierarchy.get(target_role, 99)
