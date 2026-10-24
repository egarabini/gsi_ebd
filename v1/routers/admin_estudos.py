"""Telas do Admin: lista, criacao, liberacao e nova versao do Estudo."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select

from gsi_ebd.models import Estudo, Obra, User
from gsi_ebd.services import flow_estudo
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from v1.auth import exigir, verificar_csrf, verificar_h14
from v1.db import sessao
from v1.views import (
    aplicar_trabalho_estudo,
    conteudo_estudo_form,
    contexto_estudo,
    obter_estudo,
    render,
)

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])
ADMIN = exigir("rota:/admin/estudos")
NOVA = exigir("rota:/admin/estudos/nova")


@router.get("/admin/estudos")
def lista(request: Request, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    estudos = session.exec(select(Estudo).order_by(Estudo.id)).all()
    return render(request, "admin/estudos_lista.html", {"titulo": "Estudos", "estudos": estudos})


@router.get("/admin/estudos/nova")
def nova(request: Request, session=Depends(sessao), usuario: User = Depends(NOVA)):
    obras = session.exec(select(Obra).order_by(Obra.id)).all()
    return render(
        request,
        "admin/estudos_nova.html",
        {"titulo": "Novo estudo", "erro": "", "obras": obras},
    )


@router.post("/admin/estudos/nova")
async def criar(request: Request, session=Depends(sessao), usuario: User = Depends(NOVA)):
    form = await request.form()
    obras = session.exec(select(Obra).order_by(Obra.id)).all()
    try:
        obra_id = int(str(form.get("obra_id", "") or 0))
        obra = session.get(Obra, obra_id)
        if obra is None:
            raise FluxoBloqueado("Selecione a obra de origem")
        capitulos = conteudo_estudo_form(form)
        estudo = flow_estudo.criar(
            session,
            obra,
            usuario,
            str(form.get("titulo", "")),
            str(form.get("descricao", "")),
            capitulos,
        )
        session.commit()
    except (FluxoBloqueado, ValueError) as exc:
        session.rollback()
        return render(
            request,
            "admin/estudos_nova.html",
            {"titulo": "Novo estudo", "erro": str(exc), "obras": obras},
            status_code=409,
        )
    return RedirectResponse(f"/admin/estudos/{estudo.id}", status_code=303)


@router.get("/admin/estudos/{estudo_id}")
def detalhe(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    estudo = obter_estudo(session, estudo_id)
    ctx = contexto_estudo(session, estudo)
    ctx.update({"titulo": estudo.titulo, "erro": ""})
    return render(request, "admin/estudos_detalhe.html", ctx)


async def executar(request, estudo_id, session, usuario, acao):
    form = await request.form()
    estudo = obter_estudo(session, estudo_id)
    versao = flow_estudo.versao_corrente(session, estudo)
    try:
        if str(form.get("versao_id", versao.id)) != str(versao.id):
            raise FluxoBloqueado("A versao mudou; abra novamente o estudo")
        if acao == "liberar":
            aplicar_trabalho_estudo(session, estudo, conteudo_estudo_form(form))
            flow_estudo.liberar(session, versao, str(form.get("ajustes_descritos", "")), usuario)
        elif acao == "alterar":
            flow_estudo.alterar(session, estudo, conteudo_estudo_form(form), usuario)
        elif acao == "reenviar":
            aplicar_trabalho_estudo(session, estudo, conteudo_estudo_form(form))
            flow_estudo.reenviar(session, versao, str(form.get("ajustes_descritos", "")), usuario)
        session.commit()
    except FluxoBloqueado as exc:
        session.rollback()
        ctx = contexto_estudo(session, estudo)
        ctx.update({"titulo": estudo.titulo, "erro": str(exc)})
        return render(request, "admin/estudos_detalhe.html", ctx, status_code=409)
    return RedirectResponse(f"/admin/estudos/{estudo.id}", status_code=303)


@router.post("/admin/estudos/{estudo_id}/liberar")
async def liberar(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    return await executar(request, estudo_id, session, usuario, "liberar")


@router.post("/admin/estudos/{estudo_id}/alterar")
async def alterar(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    return await executar(request, estudo_id, session, usuario, "alterar")


@router.post("/admin/estudos/{estudo_id}/reenviar")
async def reenviar(request: Request, estudo_id: int, session=Depends(sessao), usuario: User = Depends(ADMIN)):
    return await executar(request, estudo_id, session, usuario, "reenviar")
