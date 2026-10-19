from fastapi import HTTPException
from sqlmodel import select
from gsi_ebd.models import (Obra, ObraVersao, ObraCapitulo, Adendo, ObraVersaoEvento,
                            ObraVersaoCapitulo, ObraVersaoAdendo)
from gsi_ebd.services import flow
from gsi_ebd.utils.rbac import pode
from v1.auth import dados_sessao
import json


def render(request, nome, titulo, status=200, **contexto):
    dados = dados_sessao(request)
    usuario = contexto.pop("usuario", None)
    if usuario is None:
        usuario = getattr(request.state, "usuario", None)
    return request.app.state.templates.TemplateResponse(
        request=request, name=nome, status_code=status,
        context={"titulo": titulo, "usuario": usuario, "csrf": dados["csrf"],
                 "admin": bool(usuario and pode("rota:/admin/obras", usuario.role)),
                 "revisor": bool(usuario and pode("rota:/revisor/obras", usuario.role)), **contexto})


def obter_obra(session, obra_id):
    obra = session.get(Obra, obra_id)
    if obra is None:
        raise HTTPException(404, "Obra nao encontrada")
    return obra


def versao_corrente(session, obra):
    versao = session.exec(select(ObraVersao).where(ObraVersao.obra_id == obra.id).order_by(ObraVersao.numero.desc())).first()
    if versao is None:
        raise HTTPException(404, "Versao nao encontrada")
    return versao


def trabalho(session, obra):
    caps = session.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id).order_by(ObraCapitulo.ordem)).all()
    notas = session.exec(select(Adendo).where(Adendo.obra_id == obra.id, Adendo.ambiente_id.is_(None)).order_by(Adendo.codigo)).all()
    return caps, notas


def contexto_obra(session, obra):
    versao = versao_corrente(session, obra)
    caps, notas = trabalho(session, obra)
    publicado = session.get(ObraVersao, obra.versao_liberada_id) if obra.versao_liberada_id else None
    pub_caps = session.exec(select(ObraVersaoCapitulo).where(ObraVersaoCapitulo.versao_id == publicado.id,
        ObraVersaoCapitulo.momento == "liberado", ObraVersaoCapitulo.rodada == publicado.rodada)).all() if publicado else []
    pub_notas = session.exec(select(ObraVersaoAdendo).where(ObraVersaoAdendo.versao_id == publicado.id,
        ObraVersaoAdendo.momento == "liberado", ObraVersaoAdendo.rodada == publicado.rodada)).all() if publicado else []
    eventos = session.exec(select(ObraVersaoEvento).join(ObraVersao).where(ObraVersao.obra_id == obra.id).order_by(ObraVersaoEvento.id)).all()
    trilha = [{"tipo": e.tipo, "autor": e.autor_id, "quando": e.quando, "versao": e.versao_id,
               "detalhe": json.loads(e.detalhe)} for e in eventos]
    acao_edicao = {"aguardando_admin": "liberar", "devolvida": "reenviar"}.get(versao.status)
    rotulo_edicao = {"liberar": "Liberar esta versao", "reenviar": "Reenviar a revisao"}.get(acao_edicao, "")
    return {"acao_edicao": acao_edicao, "rotulo_edicao": rotulo_edicao, "obra": obra, "versao": versao, "publicado": publicado, "capitulos": caps,
            "adendos": notas, "publicados": pub_caps, "notas_publicadas": pub_notas,
            "eventos": trilha, "hash_esperado": flow.hash_obra(session, obra.id),
            "diferencas": flow.diferenca(session, versao, atual=versao.status != "liberada"),
            "parecer": versao.parecer, "ajustes_propostos": json.loads(versao.ajustes_propostos)}


def conteudo_form(form):
    from gsi_ebd.services.erros_fluxo import FluxoBloqueado
    try:
        ordens, titulos, textos = (form.getlist(k) for k in ("capitulo_ordem", "capitulo_titulo", "capitulo_texto"))
        codigos, notas, corpos = (form.getlist(k) for k in ("adendo_codigo", "adendo_titulo", "adendo_texto"))
        if not (len(ordens) == len(titulos) == len(textos) and len(codigos) == len(notas) == len(corpos)):
            raise ValueError()
        caps = [{"ordem": int(o), "titulo": t, "conteudo_md": c} for o, t, c in zip(ordens, titulos, textos)]
        adendos = [{"codigo": k, "titulo": t, "texto": c} for k, t, c in zip(codigos, notas, corpos) if k.strip()]
        if len({c["ordem"] for c in caps}) != len(caps) or len({a["codigo"] for a in adendos}) != len(adendos):
            raise ValueError()
        return {"capitulos": caps, "adendos": adendos}
    except (ValueError, TypeError):
        raise FluxoBloqueado("Conteudo do formulario invalido") from None


def aplicar_trabalho(session, obra, conteudo, autor):
    # Adaptacao dos campos de formulario; a transicao e o commit continuam separados.
    caps, notas = trabalho(session, obra)
    por_ordem = {c.ordem: c for c in caps}
    por_codigo = {a.codigo: a for a in notas}
    for item in conteudo["capitulos"]:
        cap = por_ordem.get(item["ordem"]) or ObraCapitulo(obra_id=obra.id, ordem=item["ordem"])
        cap.titulo, cap.conteudo_md = item["titulo"], item["conteudo_md"]
        session.add(cap)
    for item in conteudo["adendos"]:
        nota = por_codigo.get(item["codigo"]) or Adendo(obra_id=obra.id, codigo=item["codigo"], autor_id=autor.id)
        nota.titulo, nota.texto = item["titulo"], item["texto"]
        session.add(nota)
    session.flush()
