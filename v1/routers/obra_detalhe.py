"""Catalogo compartilhado: Admin e Revisor leem a obra publicada x a corrente."""
from fastapi import APIRouter, Depends, Request
from sqlmodel import select

from gsi_ebd.models import Obra, User
from v1.auth import exigir, verificar_csrf, verificar_h14
from v1.db import sessao
from v1.views import contexto_obra, obter_obra, render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])
CATALOGO = exigir("rota:/obras")


@router.get("/obras")
def lista(request: Request, session=Depends(sessao), usuario: User = Depends(CATALOGO)):
    obras = session.exec(select(Obra).order_by(Obra.id)).all()
    return render(request, "obras/lista.html", {"titulo": "Catalogo de obras", "obras": obras})


@router.get("/obras/{obra_id}")
def detalhe(request: Request, obra_id: int, session=Depends(sessao), usuario: User = Depends(CATALOGO)):
    obra = obter_obra(session, obra_id)
    ctx = contexto_obra(session, obra)
    ctx.update({"titulo": obra.titulo, "erro": ""})
    return render(request, "obra.html", ctx)
