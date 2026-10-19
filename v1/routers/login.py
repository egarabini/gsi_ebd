from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select
from gsi_ebd.models import User
from gsi_ebd.services.user_status_service import UserStatusService
from v1.auth import destino, exige, hash_senha, senha_confere, usuario_opcional
from v1.db import sessao
from v1.views import render

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    return render(request, "login.html", titulo="Entrar", erro="")


@router.post("/login")
async def login(request: Request, session=Depends(sessao)):
    form = await request.form()
    usuario = session.exec(select(User).where(User.email == str(form.get("email", "")).strip())).first()
    if usuario is None or not usuario.is_active or not senha_confere(str(form.get("senha", "")), usuario.password_hash):
        return render(request, "login.html", titulo="Entrar", erro="Email ou senha invalidos", status=401)
    UserStatusService.on_login_success(session, usuario)
    session.commit()
    request.app.state.sessoes.renovar(request, usuario.id)
    return RedirectResponse(destino(usuario), status_code=303)


@router.post("/logout")
def logout(request: Request, usuario=Depends(exige("rota:/perfil/alterar-senha"))):
    request.app.state.sessoes.renovar(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/perfil/alterar-senha")
def perfil_form(request: Request, usuario=Depends(exige("rota:/perfil/alterar-senha"))):
    return render(request, "perfil_senha.html", titulo="Alterar senha", usuario=usuario, erro="")


@router.post("/perfil/alterar-senha")
async def perfil(request: Request, session=Depends(sessao), usuario=Depends(exige("rota:/perfil/alterar-senha"))):
    form = await request.form()
    atual, nova, confirma = (str(form.get(k, "")) for k in ("senha_atual", "nova_senha", "confirma_senha"))
    if (not senha_confere(atual, usuario.password_hash) or len(nova) < 8
            or len(nova.encode()) > 72 or nova != confirma or nova == atual):
        return render(request, "perfil_senha.html", titulo="Alterar senha", usuario=usuario,
                      erro="Confira a senha atual, a confirmacao e use uma nova senha de 8 a 72 bytes", status=400)
    usuario.password_hash = hash_senha(nova)
    usuario.must_change_password = False
    session.add(usuario)
    session.commit()
    request.app.state.sessoes.revogar_usuario(usuario.id)
    request.app.state.sessoes.renovar(request, usuario.id)
    return RedirectResponse(destino(usuario), status_code=303)
