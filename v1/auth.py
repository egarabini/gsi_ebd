import secrets
import time
from threading import RLock
from types import SimpleNamespace
import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlmodel import select
from gsi_ebd.models import User
from gsi_ebd.services.auth_service import AuthService
from gsi_ebd.utils.rbac import PERMISSOES, pode
from v1.db import sessao


class Sessoes:
    def __init__(self, duracao=3600):
        self.duracao = duracao
        self.dados = {}
        self.lock = RLock()

    def obter(self, request):
        with self.lock:
            sid = request.session.get("sid")
            dados = self.dados.get(sid)
            if dados is None or dados["expira"] <= time.time():
                self.dados.pop(sid, None)
                sid = secrets.token_urlsafe(32)
                dados = {"usuario_id": None, "csrf": secrets.token_urlsafe(32),
                         "expira": time.time() + self.duracao}
                self.dados[sid] = dados
                request.session.clear()
                request.session["sid"] = sid
            return dados

    def renovar(self, request, usuario_id=None):
        with self.lock:
            self.dados.pop(request.session.get("sid"), None)
            request.session.clear()
            dados = self.obter(request)
            dados["usuario_id"] = usuario_id

    def revogar_usuario(self, usuario_id):
        with self.lock:
            for sid in list(self.dados):
                if self.dados[sid]["usuario_id"] == usuario_id:
                    del self.dados[sid]


def dados_sessao(request):
    return request.app.state.sessoes.obter(request)


def usuario_opcional(request: Request, session=Depends(sessao)):
    uid = dados_sessao(request)["usuario_id"]
    usuario = session.get(User, uid) if uid else None
    if usuario is not None and not usuario.is_active:
        request.app.state.sessoes.renovar(request)
        usuario = None
    request.state.usuario = SimpleNamespace(
        id=usuario.id, role=usuario.role, nome_base=usuario.nome_base,
        must_change_password=usuario.must_change_password,
    ) if usuario is not None else None
    return usuario


def usuario_atual(usuario=Depends(usuario_opcional)):
    if usuario is None:
        raise HTTPException(401, "Entre para continuar")
    return usuario


def verificar_h14(request: Request, usuario=Depends(usuario_opcional)):
    if usuario and usuario.must_change_password and request.url.path not in {"/perfil/alterar-senha", "/logout"}:
        raise HTTPException(403, "Troque sua senha antes de continuar")


async def verificar_csrf(request: Request):
    if request.method == "POST":
        form = await request.form()
        token = request.headers.get("X-CSRF-Token") or form.get("csrf_token", "")
        esperado = dados_sessao(request)["csrf"]
        if not isinstance(token, str) or not secrets.compare_digest(token, esperado):
            raise HTTPException(403, "Formulario expirado ou CSRF invalido")


def exige(chave):
    def dependencia(usuario=Depends(usuario_atual)):
        if not AuthService.can_access_role(usuario.role, PERMISSOES.get(chave, ())):
            raise HTTPException(403, "Papel sem permissao para esta rota")
        return usuario
    dependencia.chave_permissao = chave
    return dependencia


def destino(usuario):
    if usuario.must_change_password:
        return "/perfil/alterar-senha"
    if pode("rota:/admin/obras", usuario.role):
        return "/admin/obras"
    if pode("rota:/revisor/obras", usuario.role):
        return "/revisor/obras"
    return "/perfil/alterar-senha"


def senha_confere(senha, hash_senha):
    try:
        return bcrypt.checkpw(senha.encode(), hash_senha.encode())
    except (ValueError, TypeError):
        return False


def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
