"""Fluxo editorial do Estudo (ADR-020). A transacao pertence ao chamador."""
from datetime import datetime, timezone
import json

from sqlmodel import Session, select

from gsi_ebd.models import (
    Estudo,
    EstudoCapitulo,
    EstudoVersao,
    EstudoVersaoCapitulo,
    Obra,
    Role,
    User,
)
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from gsi_ebd.services.flow import _hash_json, _normalizar, hash_canonico, exigir_papel


def _agora():
    return datetime.now(timezone.utc)


def hash_estudo_capitulo(capitulo) -> str:
    return _hash_json(
        {
            "ordem": capitulo.ordem,
            "titulo": capitulo.titulo,
            "conteudo_md": capitulo.conteudo_md,
            "questions_json": capitulo.questions_json or "[]",
        }
    )


def hash_estudo(sessao: Session, estudo_id: int) -> str:
    capitulos = sessao.exec(
        select(EstudoCapitulo).where(EstudoCapitulo.estudo_id == estudo_id)
    ).all()
    return _hash_capitulos(capitulos)


def _hash_capitulos(capitulos) -> str:
    return hash_canonico({f"capitulo:{c.ordem}": hash_estudo_capitulo(c) for c in capitulos})


def _autor(usuario, papel):
    exigir_papel(usuario, papel)
    if usuario.id is None:
        raise FluxoBloqueado("Autor sem identificador")


def _estudo(sessao, estudo_id):
    estudo = sessao.exec(select(Estudo).where(Estudo.id == estudo_id).with_for_update()).one_or_none()
    if estudo is None:
        raise FluxoBloqueado("Estudo inexistente")
    return estudo


def _estado(sessao, versao, esperado):
    estudo = _estudo(sessao, versao.estudo_id)
    atual = sessao.get(EstudoVersao, versao.id, populate_existing=True)
    aceitos = (esperado,) if isinstance(esperado, str) else esperado
    if atual is None or atual.status not in aceitos:
        raise FluxoBloqueado("Transicao invalida")
    return estudo, atual


def _trabalho(sessao, estudo_id):
    capitulos = sessao.exec(
        select(EstudoCapitulo).where(EstudoCapitulo.estudo_id == estudo_id)
    ).all()
    if not capitulos:
        raise FluxoBloqueado("Estudo sem capitulos")
    if len({c.ordem for c in capitulos}) != len(capitulos):
        raise FluxoBloqueado("Ordem de capitulo duplicada")
    return capitulos


def _congelar(sessao, versao, momento, capitulos):
    for capitulo in capitulos:
        sessao.add(
            EstudoVersaoCapitulo(
                versao_id=versao.id,
                momento=momento,
                rodada=versao.rodada,
                ordem=capitulo.ordem,
                titulo=_normalizar(capitulo.titulo),
                conteudo_md=_normalizar(capitulo.conteudo_md),
                questions_json=_normalizar(capitulo.questions_json or "[]"),
                item_hash=hash_estudo_capitulo(capitulo),
            )
        )


def _publicar_estado(sessao, estudo, versao):
    estudo.status = versao.status
    sessao.add_all([estudo, versao])
    sessao.flush()


def _gravar_capitulos(sessao, estudo_id, capitulos):
    if not capitulos:
        raise FluxoBloqueado("Informe ao menos um capitulo")
    if len({item["ordem"] for item in capitulos}) != len(capitulos):
        raise FluxoBloqueado("Ordem de capitulo duplicada")
    existentes = sessao.exec(select(EstudoCapitulo).where(EstudoCapitulo.estudo_id == estudo_id)).all()
    for velho in existentes:
        sessao.delete(velho)
    sessao.flush()
    gravados = []
    for item in capitulos:
        cap = EstudoCapitulo(
            estudo_id=estudo_id,
            ordem=int(item["ordem"]),
            titulo=item.get("titulo", ""),
            conteudo_md=item.get("conteudo_md", ""),
            questions_json=item.get("questions_json") or "[]",
            status="em_revisao",
            created_at=_agora(),
        )
        sessao.add(cap)
        gravados.append(cap)
    sessao.flush()
    return gravados


def versao_corrente(sessao: Session, estudo: Estudo) -> EstudoVersao:
    versao = sessao.exec(
        select(EstudoVersao).where(EstudoVersao.estudo_id == estudo.id).order_by(EstudoVersao.numero.desc())
    ).first()
    if versao is None:
        raise FluxoBloqueado("Versao do estudo inexistente")
    return versao


def versao_liberada(sessao: Session, estudo: Estudo) -> EstudoVersao | None:
    return sessao.exec(
        select(EstudoVersao)
        .where(EstudoVersao.estudo_id == estudo.id, EstudoVersao.status == "liberada")
        .order_by(EstudoVersao.numero.desc())
    ).first()


def criar(sessao: Session, obra: Obra, admin: User, titulo: str, descricao: str, capitulos: list) -> Estudo:
    _autor(admin, Role.ADMIN)
    if sessao.get(Obra, obra.id) is None:
        raise FluxoBloqueado("Obra inexistente")
    titulo = (titulo or "").strip()
    if not titulo:
        raise FluxoBloqueado("Informe o titulo do estudo")
    estudo = Estudo(
        obra_id=obra.id,
        titulo=titulo,
        descricao=descricao or "",
        status="em_revisao",
        created_at=_agora(),
    )
    sessao.add(estudo)
    sessao.flush()
    _gravar_capitulos(sessao, estudo.id, capitulos)
    versao = EstudoVersao(
        estudo_id=estudo.id,
        numero=1,
        status="em_revisao",
        admin_id=admin.id,
        created_at=_agora(),
        conteudo_hash=hash_estudo(sessao, estudo.id),
    )
    sessao.add(versao)
    sessao.flush()
    _publicar_estado(sessao, estudo, versao)
    return estudo


def _conferir_visto(sessao, versao, hash_esperado):
    capitulos = _trabalho(sessao, versao.estudo_id)
    atual = _hash_capitulos(capitulos)
    if hash_esperado and atual != hash_esperado:
        raise FluxoBloqueado("O conteudo mudou desde que voce abriu")
    return capitulos, atual


def revisar(sessao, versao, parecer: str, ajustes: list[str], revisor: User, hash_esperado: str) -> EstudoVersao:
    _autor(revisor, Role.REVISOR)
    estudo, versao = _estado(sessao, versao, "em_revisao")
    capitulos, atual = _conferir_visto(sessao, versao, hash_esperado)
    if not parecer.strip() or not isinstance(ajustes, list) or not all(isinstance(a, str) for a in ajustes):
        raise FluxoBloqueado("Parecer e lista de ajustes obrigatorios")
    versao.rodada += 1
    _congelar(sessao, versao, "visto", capitulos)
    versao.parecer = parecer
    versao.ajustes_propostos = json.dumps(ajustes, ensure_ascii=True)
    versao.revisor_id = revisor.id
    versao.revisado_em = _agora()
    versao.hash_visto = atual
    versao.conteudo_hash = atual
    versao.status = "aguardando_admin"
    _publicar_estado(sessao, estudo, versao)
    return versao


def recusar(sessao, versao, parecer: str, revisor: User, hash_esperado: str) -> EstudoVersao:
    _autor(revisor, Role.REVISOR)
    estudo, versao = _estado(sessao, versao, ("em_revisao", "aguardando_admin"))
    _, atual = _conferir_visto(sessao, versao, hash_esperado)
    if not parecer.strip():
        raise FluxoBloqueado("Parecer obrigatorio")
    versao.parecer = parecer
    versao.revisor_id = revisor.id
    versao.revisado_em = _agora()
    versao.hash_visto = atual
    versao.conteudo_hash = atual
    versao.status = "devolvida"
    _publicar_estado(sessao, estudo, versao)
    return versao


def reenviar(sessao, versao, ajustes: str, admin: User) -> EstudoVersao:
    _autor(admin, Role.ADMIN)
    estudo, versao = _estado(sessao, versao, "devolvida")
    if not ajustes.strip():
        raise FluxoBloqueado("Descreva os ajustes")
    versao.ajustes_descritos = ajustes
    versao.admin_id = admin.id
    versao.conteudo_hash = hash_estudo(sessao, estudo.id)
    versao.status = "em_revisao"
    _publicar_estado(sessao, estudo, versao)
    return versao


def liberar(sessao, versao, ajustes_descritos: str, admin: User) -> EstudoVersao:
    _autor(admin, Role.ADMIN)
    estudo, versao = _estado(sessao, versao, "aguardando_admin")
    if versao.revisor_id is None:
        raise FluxoBloqueado("Assinatura do revisor ausente")
    if versao.revisado_em is None or not versao.hash_visto:
        raise FluxoBloqueado("Assinatura incompleta")
    if not ajustes_descritos.strip():
        raise FluxoBloqueado("Descreva os ajustes")
    capitulos = _trabalho(sessao, estudo.id)
    _congelar(sessao, versao, "liberado", capitulos)
    versao.ajustes_descritos = ajustes_descritos
    versao.admin_id = admin.id
    versao.liberada_em = _agora()
    versao.hash_liberado = _hash_capitulos(capitulos)
    versao.conteudo_hash = versao.hash_liberado
    versao.status = "liberada"
    anteriores = sessao.exec(
        select(EstudoVersao).where(
            EstudoVersao.estudo_id == estudo.id,
            EstudoVersao.id != versao.id,
            EstudoVersao.status == "liberada",
        )
    ).all()
    for anterior in anteriores:
        anterior.status = "substituida"
        sessao.add(anterior)
    _publicar_estado(sessao, estudo, versao)
    return versao


def alterar(sessao, estudo: Estudo, capitulos: list, admin: User) -> EstudoVersao:
    _autor(admin, Role.ADMIN)
    estudo = _estudo(sessao, estudo.id)
    atual = versao_corrente(sessao, estudo)
    if atual.status != "liberada":
        raise FluxoBloqueado("Estudo ainda nao liberado")
    pendentes = sessao.exec(
        select(EstudoVersao).where(
            EstudoVersao.estudo_id == estudo.id,
            EstudoVersao.status.in_(["em_revisao", "aguardando_admin", "devolvida"]),
        )
    ).all()
    if pendentes:
        raise FluxoBloqueado("Estudo ja possui ciclo pendente")
    _gravar_capitulos(sessao, estudo.id, capitulos)
    nova = EstudoVersao(
        estudo_id=estudo.id,
        numero=atual.numero + 1,
        status="em_revisao",
        admin_id=admin.id,
        created_at=_agora(),
        conteudo_hash=hash_estudo(sessao, estudo.id),
    )
    sessao.add(nova)
    sessao.flush()
    _publicar_estado(sessao, estudo, nova)
    return nova
