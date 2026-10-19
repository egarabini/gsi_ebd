from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select
from gsi_ebd.models import Obra, ObraVersao
from gsi_ebd.services import flow
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from v1.auth import exige
from v1.db import sessao
from v1.views import render, obter_obra, versao_corrente, contexto_obra

router = APIRouter()
REVISOR = exige("rota:/revisor/obras")


@router.get("/revisor/obras")
def fila(request: Request, session=Depends(sessao), usuario=Depends(REVISOR)):
    obras = session.exec(select(Obra).join(ObraVersao, ObraVersao.obra_id == Obra.id).where(
        ObraVersao.status.in_(["em_revisao", "aguardando_admin"])).distinct()).all()
    publicadas = session.exec(select(Obra).where(Obra.versao_liberada_id.is_not(None))).all()
    return render(request, "revisor/lista.html", titulo="Fila de revisao", usuario=usuario,
                  obras=obras, publicadas=publicadas)


@router.get("/revisor/obras/{obra_id}")
def detalhe(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(REVISOR)):
    obra = obter_obra(session, obra_id)
    return render(request, "revisor/detalhe.html", titulo=obra.titulo, usuario=usuario, erro="", **contexto_obra(session, obra))


async def executar(request, obra_id, session, usuario, acao):
    form = await request.form()
    obra = obter_obra(session, obra_id)
    versao = versao_corrente(session, obra)
    try:
        if acao == "solicitar":
            if obra.versao_liberada_id is None:
                raise FluxoBloqueado("Obra ainda nao liberada")
            versao = session.get(ObraVersao, obra.versao_liberada_id)
        if str(form.get("versao_id", versao.id)) != str(versao.id):
            raise FluxoBloqueado("A versao mudou; abra novamente a obra")
        parecer = str(form.get("parecer", ""))
        esperado = str(form.get("hash_esperado", ""))
        if acao == "revisar":
            ajustes = [item.strip() for item in str(form.get("ajustes", "")).splitlines() if item.strip()]
            flow.revisar(session, versao, parecer, ajustes, usuario, esperado)
        elif acao == "recusar":
            flow.recusar(session, versao, parecer, usuario, esperado)
        elif acao == "solicitar":
            flow.solicitar_revisao(session, versao, usuario, str(form.get("motivo", "")))
        elif acao == "posicionar":
            flow.posicionar(session, versao, usuario, str(form.get("posicao", "")), str(form.get("texto", "")))
        session.commit()
    except FluxoBloqueado as exc:
        session.rollback()
        return render(request, "revisor/detalhe.html", titulo=obra.titulo, usuario=usuario,
                      erro=str(exc), status=409, **contexto_obra(session, obra))
    return RedirectResponse(f"/revisor/obras/{obra.id}", status_code=303)


@router.post("/revisor/obras/{obra_id}/revisar")
async def revisar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(REVISOR)):
    return await executar(request, obra_id, session, usuario, "revisar")


@router.post("/revisor/obras/{obra_id}/recusar")
async def recusar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(REVISOR)):
    return await executar(request, obra_id, session, usuario, "recusar")


@router.post("/revisor/obras/{obra_id}/solicitar")
async def solicitar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(REVISOR)):
    return await executar(request, obra_id, session, usuario, "solicitar")


@router.post("/revisor/obras/{obra_id}/posicionar")
async def posicionar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(REVISOR)):
    return await executar(request, obra_id, session, usuario, "posicionar")
