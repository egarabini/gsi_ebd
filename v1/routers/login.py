"""Login, logout e troca de senha. A regra de status fica no dominio."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from gsi_ebd.models import Role, User, UserStatus
from gsi_ebd.services.user_status_service import UserStatusService
from v1.auth import (
    destino,
    exigir,
    hash_senha,
    senha_confere,
    usuario_opcional,
    verificar_csrf,
    verificar_h14,
)
from v1.db import sessao
from v1.views import render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])


def _mensagem_de_status(usuario: User) -> str | None:
    # A mesma porta do estado Reflex: o admin nao e barrado pelo status.
    if int(usuario.role) == int(Role.ADMIN):
        return None
    if usuario.status == UserStatus.CANCELADO:
        return "Acesso não permitido. Entre em contato com o administrador."
    if usuario.status == UserStatus.INATIVO:
        return "Conta inativa. Confirme o interesse para reativar o acesso."
    if usuario.status == UserStatus.SUSPENSO:
        return "Conta suspensa. Verifique seu email para ativar o acesso."
    if usuario.status != UserStatus.ATIVO:
        return "Acesso não permitido."
    return None


@router.get("/login")
def pagina_login(request: Request, usuario=Depends(usuario_opcional)):
    return render(request, "login.html", {"erro": ""})


@router.post("/login")
def entrar(
    request: Request,
    email: str = Form(""),
    senha: str = Form(""),
    session: Session = Depends(sessao),
):
    usuario = session.exec(select(User).where(User.email == email.strip())).first()
    if usuario is None:
        return render(request, "login.html", {"erro": "Credenciais inválidas."}, status_code=401)
    bloqueio = _mensagem_de_status(usuario)
    if bloqueio:
        return render(request, "login.html", {"erro": bloqueio}, status_code=401)
    if not senha_confere(senha, usuario.password_hash):
        UserStatusService.on_login_failure(session, usuario)
        session.commit()
        return render(request, "login.html", {"erro": "Credenciais inválidas."}, status_code=401)
    UserStatusService.on_login_success(session, usuario)
    session.commit()
    request.app.state.sessoes.renovar(request, usuario.id)
    return RedirectResponse(destino(request, usuario), status_code=303)


@router.post("/logout")
def sair(request: Request, usuario: User = Depends(exigir("rota:/perfil/alterar-senha"))):
    request.app.state.sessoes.revogar_usuario(usuario.id)
    request.app.state.sessoes.renovar(request)
    return RedirectResponse("/login", status_code=303)


def _erro_de_troca(usuario: User, atual: str, nova: str, confirma: str) -> str:
    if not atual:
        return "Informe a senha atual."
    if len(nova) < 8:
        return "A nova senha deve ter ao menos 8 caracteres."
    # bcrypt recusa senha maior que 72 bytes; sem este corte o pedido vira 500.
    if len(nova.encode()) > 72:
        return "A nova senha é longa demais."
    if nova != confirma:
        return "As senhas não coincidem."
    if not senha_confere(atual, usuario.password_hash):
        return "Senha atual incorreta."
    if senha_confere(nova, usuario.password_hash):
        return "A nova senha não pode ser igual à senha atual."
    return ""


@router.get("/perfil/alterar-senha")
def pagina_senha(request: Request, usuario: User = Depends(exigir("rota:/perfil/alterar-senha"))):
    return render(request, "perfil_senha.html", {"erro": "", "ok": ""})


@router.post("/perfil/alterar-senha")
def trocar_senha(
    request: Request,
    senha_atual: str = Form(""),
    nova_senha: str = Form(""),
    confirma_senha: str = Form(""),
    usuario: User = Depends(exigir("rota:/perfil/alterar-senha")),
    session: Session = Depends(sessao),
):
    # A sessao da dependencia pode ser outra instancia; recarrega na transacao.
    atual = session.get(User, usuario.id)
    erro = _erro_de_troca(atual, senha_atual, nova_senha, confirma_senha)
    if erro:
        return render(request, "perfil_senha.html", {"erro": erro, "ok": ""}, status_code=400)
    atual.password_hash = hash_senha(nova_senha)
    atual.must_change_password = False
    session.add(atual)
    session.commit()
    request.app.state.sessoes.revogar_usuario(atual.id)
    request.app.state.sessoes.renovar(request, atual.id)
    return RedirectResponse("/", status_code=303)
