"""Telas do Revisor: fila, parecer e recusa do Estudo."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from gsi_ebd.models import Estudo, EstudoVersao, User
from gsi_ebd.services import flow_estudo
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from v1.auth import exigir, verificar_csrf, verificar_h14
from v1.db import sessao
from v1.views import contexto_estudo, obter_estudo, render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])
REVISOR = exigir("rota:/revisor/avaliacoes")
FILA = ("em_revisao", "aguardando_admin")


@router.get("/revisor/avaliacoes")
def fila(request: Request, session=Depends(sessao), usuario: User = Depends(REVISOR)):
    estudos = session.exec(
        select(Estudo)
        .join(EstudoVersao, EstudoVersao.estudo_id == Estudo.id)
        .where(EstudoVersao.status.in_(list(FILA)))
        .distinct()
    ).all()
    return render(
        request,
        "revisor/avaliacoes_lista.html",
        {"titulo": "Avaliacoes", "estudos": estudos},
    )


@router.get("/revisor/avaliacoes/{estudo_id}")
def detalhe(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(REVISOR)):
    estudo = obter_estudo(session, estudo_id)
    ctx = contexto_estudo(session, estudo)
    ctx.update({"titulo": estudo.titulo, "erro": ""})
    return render(request, "revisor/avaliacoes_detalhe.html", ctx)


async def executar(request, estudo_id, session, usuario, acao):
    form = await request.form()
    estudo = obter_estudo(session, estudo_id)
    versao = flow_estudo.versao_corrente(session, estudo)
    try:
        if str(form.get("versao_id", versao.id)) != str(versao.id):
            raise FluxoBloqueado("A versao mudou; abra novamente o estudo")
        parecer = str(form.get("parecer", ""))
        esperado = str(form.get("hash_esperado", ""))
        if acao == "revisar":
            ajustes = [item.strip() for item in str(form.get("ajustes", "")).splitlines() if item.strip()]
            flow_estudo.revisar(session, versao, parecer, ajustes, usuario, esperado)
        elif acao == "recusar":
            flow_estudo.recusar(session, versao, parecer, usuario, esperado)
        session.commit()
    except FluxoBloqueado as exc:
        session.rollback()
        ctx = contexto_estudo(session, estudo)
        ctx.update({"titulo": estudo.titulo, "erro": str(exc)})
        return render(request, "revisor/avaliacoes_detalhe.html", ctx, status_code=409)
    return RedirectResponse(f"/revisor/avaliacoes/{estudo.id}", status_code=303)


@router.post("/revisor/avaliacoes/{estudo_id}/revisar")
async def revisar(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(REVISOR)):
    return await executar(request, estudo_id, session, usuario, "revisar")


@router.post("/revisor/avaliacoes/{estudo_id}/recusar")
async def recusar(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(REVISOR)):
    return await executar(request, estudo_id, session, usuario, "recusar")
