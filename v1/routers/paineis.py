"""Paineis so leitura do Admin e do Revisor (DEM-017 fatia 1)."""
from fastapi import APIRouter, Depends, Request

from gsi_ebd.models import User
from v1.auth import exigir, verificar_csrf, verificar_h14
from v1.db import sessao
from v1.paineis import resumo_admin, resumo_revisor
from v1.views import render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])
ADMIN = exigir("rota:/admin")
REVISOR = exigir("rota:/revisor")


@router.get("/admin")
def painel_admin(request: Request, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    ctx = resumo_admin(session)
    ctx["titulo"] = "Painel do administrador"
    return render(request, "admin/painel.html", ctx)


@router.get("/revisor")
def painel_revisor(request: Request, session=Depends(sessao), usuario: User = Depends(REVISOR)):
    ctx = resumo_revisor(session)
    ctx["titulo"] = "Painel do revisor"
    return render(request, "revisor/painel.html", ctx)
