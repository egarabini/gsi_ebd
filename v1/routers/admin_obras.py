from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select
from gsi_ebd.models import Obra
from gsi_ebd.services import flow
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from v1.auth import exige
from v1.db import sessao
from v1.views import render, obter_obra, versao_corrente, contexto_obra, conteudo_form, aplicar_trabalho

router = APIRouter()
ADMIN = exige("rota:/admin/obras")


@router.get("/admin/obras")
def lista(request: Request, session=Depends(sessao), usuario=Depends(ADMIN)):
    obras = session.exec(select(Obra).order_by(Obra.id)).all()
    return render(request, "admin/lista.html", titulo="Obras", usuario=usuario, obras=obras)


@router.get("/admin/obras/nova")
def nova(request: Request, usuario=Depends(ADMIN)):
    return render(request, "admin/nova.html", titulo="Importar obra", usuario=usuario, erro="")


@router.post("/admin/obras")
async def importar(request: Request, session=Depends(sessao), usuario=Depends(ADMIN)):
    form = await request.form()
    try:
        titulo = str(form.get("titulo", "")).strip()
        if not titulo:
            raise FluxoBloqueado("Informe o titulo da obra")
        conteudo = conteudo_form(form)
        obra = Obra(titulo=titulo, descricao=str(form.get("descricao", "")), origem=str(form.get("origem", "")))
        flow.importar(session, str(form.get("fonte_id", "")).strip(), obra, usuario)
        aplicar_trabalho(session, obra, conteudo, usuario)
        session.commit()
    except (FluxoBloqueado, OSError) as exc:
        session.rollback()
        mensagem = str(exc) if isinstance(exc, FluxoBloqueado) else "Inventario indisponivel"
        return render(request, "admin/nova.html", titulo="Importar obra", usuario=usuario, erro=mensagem, status=409)
    return RedirectResponse(f"/admin/obras/{obra.id}", status_code=303)


@router.get("/admin/obras/{obra_id}")
def detalhe(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    obra = obter_obra(session, obra_id)
    return render(request, "admin/detalhe.html", titulo=obra.titulo, usuario=usuario, erro="", **contexto_obra(session, obra))


async def executar(request, obra_id, session, usuario, acao):
    form = await request.form()
    obra = obter_obra(session, obra_id)
    versao = versao_corrente(session, obra)
    try:
        if str(form.get("versao_id", versao.id)) != str(versao.id):
            raise FluxoBloqueado("A versao mudou; abra novamente a obra")
        if acao == "liberar":
            conteudo = conteudo_form(form)
            aplicar_trabalho(session, obra, conteudo, usuario)
            flow.liberar(session, versao, str(form.get("ajustes_descritos", "")), usuario)
        elif acao == "alterar":
            flow.alterar(session, obra, conteudo_form(form), usuario)
        elif acao == "reenviar":
            aplicar_trabalho(session, obra, conteudo_form(form), usuario)
            flow.reenviar(session, versao, str(form.get("ajustes_descritos", "")), usuario)
        elif acao == "aceitar":
            flow.aceitar_solicitacao(session, obra, usuario)
        elif acao == "dispensar":
            flow.dispensar_solicitacao(session, obra, usuario, str(form.get("motivo", "")))
        elif acao == "cancelar":
            flow.cancelar_ciclo(session, obra, usuario)
        session.commit()
    except (FluxoBloqueado, OSError) as exc:
        session.rollback()
        mensagem = str(exc) if isinstance(exc, FluxoBloqueado) else "Inventario indisponivel"
        return render(request, "admin/detalhe.html", titulo=obra.titulo, usuario=usuario,
                      erro=mensagem, status=409, **contexto_obra(session, obra))
    return RedirectResponse(f"/admin/obras/{obra.id}", status_code=303)


@router.post("/admin/obras/{obra_id}/liberar")
async def liberar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "liberar")


@router.post("/admin/obras/{obra_id}/alterar")
async def alterar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "alterar")


@router.post("/admin/obras/{obra_id}/reenviar")
async def reenviar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "reenviar")


@router.post("/admin/obras/{obra_id}/aceitar")
async def aceitar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "aceitar")


@router.post("/admin/obras/{obra_id}/dispensar")
async def dispensar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "dispensar")


@router.post("/admin/obras/{obra_id}/cancelar")
async def cancelar(request: Request, obra_id: int, session=Depends(sessao), usuario=Depends(ADMIN)):
    return await executar(request, obra_id, session, usuario, "cancelar")
