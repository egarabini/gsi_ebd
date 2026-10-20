"""Interface de identidade da v1 e a implementacao minima propria.

O marco 1b substitui estas tres funcoes sem trocar as telas:
usuario_atual, exigir, ambiente_atual.
"""
import secrets
import time
from threading import RLock

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from gsi_ebd.models import Ambiente, User
from gsi_ebd.services.auth_service import AuthService
from gsi_ebd.utils.rbac import pode
from v1.db import sessao

# Com a flag ligada, so a troca e o logout passam (H-14).
LIBERADAS_COM_TROCA_PENDENTE = {"/perfil/alterar-senha", "/logout"}
DURACAO_SESSAO = 3600


class Sessoes:
    """Sessao de servidor. O cookie so guarda o sid; o estado fica aqui."""

    def __init__(self, duracao=DURACAO_SESSAO):
        self.duracao = duracao
        self.dados = {}
        self.lock = RLock()

    def obter(self, request: Request):
        with self.lock:
            sid = request.session.get("sid")
            dados = self.dados.get(sid)
            if dados is None or dados["expira"] <= time.time():
                self.dados.pop(sid, None)
                sid = secrets.token_urlsafe(32)
                dados = {
                    "usuario_id": None,
                    "csrf": secrets.token_urlsafe(32),
                    "expira": time.time() + self.duracao,
                }
                self.dados[sid] = dados
                request.session.clear()
                request.session["sid"] = sid
            return dados

    def renovar(self, request: Request, usuario_id=None):
        """Troca o sid. O login e a troca de senha nao reaproveitam o cookie antigo."""
        with self.lock:
            self.dados.pop(request.session.get("sid"), None)
            request.session.clear()
            dados = self.obter(request)
            dados["usuario_id"] = usuario_id
            return dados

    def revogar_usuario(self, usuario_id):
        with self.lock:
            for sid in list(self.dados):
                if self.dados[sid]["usuario_id"] == usuario_id:
                    del self.dados[sid]


def dados_sessao(request: Request):
    return request.app.state.sessoes.obter(request)


def usuario_opcional(request: Request, session: Session = Depends(sessao)):
    dados = dados_sessao(request)
    usuario = session.get(User, dados["usuario_id"]) if dados["usuario_id"] else None
    if usuario is not None and not usuario.is_active:
        request.app.state.sessoes.renovar(request)
        usuario = None
    request.state.usuario = usuario
    return usuario


def usuario_atual(request: Request, usuario=Depends(usuario_opcional)) -> User:
    if usuario is None:
        raise HTTPException(401, "Entre para continuar.")
    return usuario


def ambiente_atual(request: Request, usuario: User = Depends(usuario_atual), session: Session = Depends(sessao)):
    """Ambiente do usuario no Didasko. Sem vinculo, devolve None."""
    if usuario.ambiente_id is None:
        return None
    return session.get(Ambiente, usuario.ambiente_id)


def exigir(chave: str):
    """Dependencia de uma rota. A decisao e a matriz (rbac.pode), nao o cliente."""

    def dependencia(usuario: User = Depends(usuario_atual)) -> User:
        if not pode(chave, usuario.role):
            raise HTTPException(403, "Papel sem permissão para esta rota.")
        return usuario

    dependencia.chave_permissao = chave
    return dependencia


def verificar_h14(request: Request, usuario=Depends(usuario_opcional)):
    if (
        usuario is not None
        and usuario.must_change_password
        and request.url.path not in LIBERADAS_COM_TROCA_PENDENTE
    ):
        raise HTTPException(403, "Troque sua senha antes de continuar.")


async def verificar_csrf(request: Request):
    if request.method != "POST":
        return
    form = await request.form()
    enviado = request.headers.get("X-CSRF-Token") or form.get("csrf_token", "")
    esperado = dados_sessao(request)["csrf"]
    if not isinstance(enviado, str) or not secrets.compare_digest(enviado, esperado):
        raise HTTPException(403, "Formulário expirado ou CSRF inválido.")


def caminhos_da_app(app) -> set[str]:
    """Caminhos que a app realmente atende.

    No FastAPI 0.150 a rota incluida nao aparece em app.routes: fica num
    router aninhado. Olhar so o primeiro nivel faria o login ignorar uma
    casa que ja existe.
    """
    achados = set()
    pilha = list(app.routes)
    while pilha:
        rota = pilha.pop()
        contextos = getattr(rota, "effective_route_contexts", None)
        if callable(contextos):
            for ctx in contextos():
                caminho = getattr(ctx, "path", None)
                if caminho:
                    achados.add(caminho)
            continue
        caminho = getattr(rota, "path", None)
        if caminho:
            achados.add(caminho)
    return achados


def destino(request: Request, usuario: User) -> str:
    """Casa do papel quando a rota ja existe na v1; senao a raiz.

    As casas da matriz (/admin, /coordenador, /revisao, /aluno) nascem nos
    marcos seguintes. Ate la, a raiz autenticada e `/`.
    """
    if usuario.must_change_password:
        return "/perfil/alterar-senha"
    casa = AuthService.redirect_for_role(usuario.role)
    if casa in caminhos_da_app(request.app):
        return casa
    return "/"


def senha_confere(senha: str, hash_senha: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), hash_senha.encode())
    except (ValueError, TypeError):
        return False


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
