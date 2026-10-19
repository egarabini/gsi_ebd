from fastapi import APIRouter, Depends, Request
from v1.auth import exige
from v1.db import sessao
from v1.views import render, obter_obra, contexto_obra

router = APIRouter()


@router.get("/obras/{obra_id}")
def detalhe(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(exige("rota:/obras"))):
    obra = obter_obra(session, obra_id)
    return render(request, "obra.html", titulo=obra.titulo, usuario=usuario, erro="", **contexto_obra(session, obra))
