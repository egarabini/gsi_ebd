"""Fluxo editorial da obra; a transacao pertence ao chamador."""
from collections.abc import Mapping
from hashlib import sha256
from datetime import datetime, timezone
import json
import unicodedata

from sqlmodel import Session, select

from gsi_ebd.models import (
    Adendo, Ambiente, Obra, ObraCapitulo, ObraVersao, ObraVersaoAdendo,
    ObraVersaoCapitulo, ObraVersaoEvento, Role, User, VinculoObra,
)
from gsi_ebd.services.fontes import fonte_decisao
from gsi_ebd.services.erros_fluxo import FluxoBloqueado


def exigir_papel(usuario: User, papel: Role) -> None:
    if usuario.role != papel:
        raise FluxoBloqueado("Papel sem permissao para esta operacao")


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFC", texto.replace("\r\n", "\n").replace("\r", "\n"))


def _hash_json(campos: dict) -> str:
    campos = {k: _normalizar(v) if isinstance(v, str) else v for k, v in campos.items()}
    return sha256(json.dumps(
        campos, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def hash_capitulo(capitulo) -> str:
    return _hash_json({"ordem": capitulo.ordem, "titulo": capitulo.titulo,
                       "conteudo_md": capitulo.conteudo_md})


def hash_adendo(adendo) -> str:
    return _hash_json({"codigo": adendo.codigo, "titulo": adendo.titulo, "texto": adendo.texto})


def hash_canonico(itens: Mapping[str, str]) -> str:
    conteudo = "v1\n" + "\n".join(f"{k}\t{v}" for k, v in sorted(itens.items()))
    return sha256(conteudo.encode("utf-8")).hexdigest()


def tamanho_diferenca(visto: Mapping[str, str], liberado: Mapping[str, str]) -> int:
    return sum(visto.get(chave) != liberado.get(chave) for chave in visto.keys() | liberado.keys())


def hash_obra(sessao: Session, obra_id: int) -> str:
    capitulos = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra_id)).all()
    adendos = sessao.exec(select(Adendo).where(
        Adendo.obra_id == obra_id, Adendo.ambiente_id.is_(None)
    )).all()
    return _hash_itens(capitulos, adendos)


def _agora():
    return datetime.now(timezone.utc)


def _autor(usuario, papel):
    exigir_papel(usuario, papel)
    if usuario.id is None:
        raise FluxoBloqueado("Autor sem identificador")


def _obra(sessao, obra_id):
    obra = sessao.exec(select(Obra).where(Obra.id == obra_id).with_for_update()).one_or_none()
    if obra is None:
        raise FluxoBloqueado("Obra inexistente")
    return obra


def _estado(sessao, versao, esperado):
    obra = _obra(sessao, versao.obra_id)
    atual = sessao.get(ObraVersao, versao.id, populate_existing=True)
    if atual is None or atual.status not in ((esperado,) if isinstance(esperado, str) else esperado):
        raise FluxoBloqueado("Transicao invalida")
    return obra, atual


def _trabalho(sessao, obra_id):
    capitulos = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra_id)).all()
    adendos = sessao.exec(select(Adendo).where(
        Adendo.obra_id == obra_id, Adendo.ambiente_id.is_(None)
    )).all()
    if len({c.ordem for c in capitulos}) != len(capitulos):
        raise FluxoBloqueado("Ordem de capitulo duplicada")
    if len({_normalizar(a.codigo) for a in adendos}) != len(adendos):
        raise FluxoBloqueado("Codigo de adendo duplicado")
    return capitulos, adendos


def _congelar(sessao, versao, momento, capitulos, adendos):
    for capitulo in capitulos:
        sessao.add(ObraVersaoCapitulo(
            versao_id=versao.id, momento=momento, rodada=versao.rodada, ordem=capitulo.ordem,
            titulo=_normalizar(capitulo.titulo), conteudo_md=_normalizar(capitulo.conteudo_md),
            item_hash=hash_capitulo(capitulo),
        ))
    for adendo in adendos:
        sessao.add(ObraVersaoAdendo(
            versao_id=versao.id, momento=momento, rodada=versao.rodada, codigo=_normalizar(adendo.codigo),
            titulo=_normalizar(adendo.titulo), texto=_normalizar(adendo.texto),
            item_hash=hash_adendo(adendo),
        ))


def _hash_itens(capitulos, adendos):
    return hash_canonico({
        **{f"capitulo:{c.ordem}": hash_capitulo(c) for c in capitulos},
        **{f"adendo:{_normalizar(a.codigo)}": hash_adendo(a) for a in adendos},
    })


def _evento(sessao, versao, tipo, autor, **detalhe):
    evento = ObraVersaoEvento(
        versao_id=versao.id, tipo=tipo, autor_id=autor.id, quando=_agora(),
        detalhe=json.dumps({"hash": versao.conteudo_hash, "rodada": versao.rodada, **detalhe}, ensure_ascii=True),
    )
    sessao.add(evento)
    sessao.flush()
    return evento


def _publicar_estado(sessao, obra, versao):
    obra.status = versao.status
    obra.updated_at = _agora()
    sessao.add_all([obra, versao])
    sessao.flush()


def _nova_versao(sessao, obra, admin):
    versoes = sessao.exec(select(ObraVersao).where(ObraVersao.obra_id == obra.id)).all()
    if any(v.status in {"em_revisao", "aguardando_admin", "devolvida"} for v in versoes):
        raise FluxoBloqueado("Obra ja possui ciclo pendente")
    versao = ObraVersao(
        obra_id=obra.id, numero=max((v.numero for v in versoes), default=0) + 1,
        admin_id=admin.id if admin.role == Role.ADMIN else None,
        created_at=_agora(), conteudo_hash=hash_obra(sessao, obra.id),
    )
    sessao.add(versao)
    sessao.flush()
    _publicar_estado(sessao, obra, versao)
    return versao


def importar(sessao: Session, fonte: str, obra: Obra, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    if fonte_decisao(fonte, recarregar=True) == "nao_entra":
        raise FluxoBloqueado("A fonte nao entra")
    if obra.id is not None and sessao.get(Obra, obra.id) is not None:
        raise FluxoBloqueado("Obra ja importada; use alterar")
    obra.fonte_id = fonte
    obra.status = "em_revisao"
    obra.created_at = obra.created_at or _agora()
    sessao.add(obra)
    sessao.flush()
    versao = _nova_versao(sessao, obra, admin)
    _evento(sessao, versao, "importada", admin, fonte_id=fonte)
    return versao


def _conferir_visto(sessao, versao, hash_esperado):
    capitulos, adendos = _trabalho(sessao, versao.obra_id)
    atual = _hash_itens(capitulos, adendos)
    if atual != hash_esperado:
        raise FluxoBloqueado("O conteudo mudou desde que voce abriu")
    return capitulos, adendos, atual


def revisar(sessao, versao, parecer: str, ajustes: list[str], revisor: User,
            hash_esperado: str) -> ObraVersao:
    _autor(revisor, Role.REVISOR)
    obra, versao = _estado(sessao, versao, "em_revisao")
    capitulos, adendos, atual = _conferir_visto(sessao, versao, hash_esperado)
    if not parecer.strip() or not isinstance(ajustes, list) or not all(isinstance(a, str) for a in ajustes):
        raise FluxoBloqueado("Parecer e lista de ajustes obrigatorios")
    versao.rodada += 1
    _congelar(sessao, versao, "visto", capitulos, adendos)
    versao.parecer = parecer
    versao.ajustes_propostos = json.dumps(ajustes, ensure_ascii=True)
    versao.revisor_id = revisor.id
    versao.revisado_em = _agora()
    versao.hash_visto = atual
    versao.conteudo_hash = atual
    versao.status = "aguardando_admin"
    _publicar_estado(sessao, obra, versao)
    _evento(sessao, versao, "vista", revisor, parecer=parecer, ajustes=ajustes)
    return versao


def recusar(sessao, versao, parecer: str, revisor: User, hash_esperado: str) -> ObraVersao:
    _autor(revisor, Role.REVISOR)
    obra, versao = _estado(sessao, versao, ("em_revisao", "aguardando_admin"))
    _, _, atual = _conferir_visto(sessao, versao, hash_esperado)
    if not parecer.strip():
        raise FluxoBloqueado("Parecer obrigatorio")
    versao.parecer = parecer
    versao.revisor_id = revisor.id
    versao.revisado_em = _agora()
    versao.hash_visto = atual
    versao.conteudo_hash = atual
    versao.status = "devolvida"
    _publicar_estado(sessao, obra, versao)
    _evento(sessao, versao, "recusada", revisor, parecer=parecer)
    return versao


def reenviar(sessao, versao, ajustes: str, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra, versao = _estado(sessao, versao, "devolvida")
    if not ajustes.strip():
        raise FluxoBloqueado("Descreva os ajustes")
    versao.ajustes_descritos = ajustes
    versao.admin_id = admin.id
    versao.conteudo_hash = hash_obra(sessao, obra.id)
    versao.status = "em_revisao"
    _publicar_estado(sessao, obra, versao)
    _evento(sessao, versao, "reenviada", admin, ajustes=ajustes)
    return versao


def liberar(sessao, versao, ajustes_descritos: str, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra, versao = _estado(sessao, versao, "aguardando_admin")
    if versao.revisor_id is None:
        raise FluxoBloqueado("Assinatura do revisor ausente")
    if versao.revisado_em is None or not versao.hash_visto:
        raise FluxoBloqueado("Assinatura incompleta")
    if fonte_decisao(obra.fonte_id, recarregar=True) != "entra":
        raise FluxoBloqueado("A fonte nao permite liberacao")
    if not ajustes_descritos.strip():
        raise FluxoBloqueado("Descreva os ajustes")
    capitulos, adendos = _trabalho(sessao, obra.id)
    _congelar(sessao, versao, "liberado", capitulos, adendos)
    versao.ajustes_descritos = ajustes_descritos
    versao.admin_id = admin.id
    versao.liberada_em = _agora()
    versao.hash_liberado = _hash_itens(capitulos, adendos)
    versao.conteudo_hash = versao.hash_liberado
    versao.status = "liberada"
    if obra.versao_liberada_id is not None and obra.versao_liberada_id != versao.id:
        anterior = sessao.get(ObraVersao, obra.versao_liberada_id)
        anterior.status = "substituida"
        sessao.add(anterior)
    obra.status = "liberada"
    obra.disponibilidade = "aberta"
    obra.versao_liberada_id = versao.id
    _publicar_estado(sessao, obra, versao)
    _evento(sessao, versao, "liberada", admin, ajustes=ajustes_descritos,
            hash_visto=versao.hash_visto, hash_liberado=versao.hash_liberado,
            tamanho_diferenca=len(diferenca(sessao, versao)))
    return versao


def alterar(sessao, obra, conteudo: dict, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra = _obra(sessao, obra.id)
    if obra.versao_liberada_id is None:
        raise FluxoBloqueado("Obra ainda nao liberada")
    # Valida todo o conteudo antes de modificar a copia de trabalho.
    if (not isinstance(conteudo, dict)
            or not all(isinstance(conteudo.get(k), list) for k in ("capitulos", "adendos"))
            or not all(isinstance(item, dict) for k in ("capitulos", "adendos") for item in conteudo[k])):
        raise FluxoBloqueado("Conteudo malformado")
    try:
        capitulos = [ObraCapitulo.model_validate({
            "obra_id": obra.id, "ordem": item["ordem"], "titulo": item.get("titulo", ""),
            "conteudo_md": item.get("conteudo_md", ""),
        }) for item in conteudo["capitulos"]]
        adendos = [Adendo.model_validate({
            "obra_id": obra.id, "autor_id": admin.id, "codigo": item["codigo"],
            "titulo": item.get("titulo", ""), "texto": item.get("texto", ""),
            "ambiente_id": item.get("ambiente_id"),
        }) for item in conteudo["adendos"]]
    except (KeyError, TypeError, ValueError) as erro:
        raise FluxoBloqueado("Conteudo malformado") from erro
    if any(a.ambiente_id is not None for a in adendos):
        raise FluxoBloqueado("Alterar recebe somente adendos da base")
    if len({c.ordem for c in capitulos}) != len(capitulos) or len({_normalizar(a.codigo) for a in adendos}) != len(adendos):
        raise FluxoBloqueado("Itens duplicados")
    versao = _nova_versao(sessao, obra, admin)
    _suspender(sessao, obra)
    anteriores, notas = _trabalho(sessao, obra.id)
    # Preserva as identidades usadas pelos adendos de ambiente e mapas de origem.
    por_ordem = {c.ordem: c for c in anteriores}
    por_codigo = {_normalizar(a.codigo): a for a in notas}
    for novo in capitulos:
        existente = por_ordem.pop(novo.ordem, None)
        if existente is None:
            sessao.add(novo)
        else:
            existente.titulo = novo.titulo
            existente.conteudo_md = novo.conteudo_md
            sessao.add(existente)
    for novo in adendos:
        existente = por_codigo.pop(_normalizar(novo.codigo), None)
        if existente is None:
            sessao.add(novo)
        else:
            existente.titulo = novo.titulo
            existente.texto = novo.texto
            existente.autor_id = admin.id
            sessao.add(existente)
    # Omitir um item nao o remove; a politica de remocao pertence a proxima fatia.
    sessao.flush()
    versao.conteudo_hash = hash_obra(sessao, obra.id)
    sessao.add(versao)
    sessao.flush()
    _evento(sessao, versao, "alterada", admin, versao_anterior_id=obra.versao_liberada_id)
    return versao


def _suspender(sessao, obra):
    obra.disponibilidade = "suspensa_para_novos"
    obra.status = "em_revisao"
    obra.updated_at = _agora()
    sessao.add(obra)
    sessao.flush()


def _solicitacao_pendente(sessao, obra):
    eventos = sessao.exec(select(ObraVersaoEvento).join(
        ObraVersao, ObraVersao.id == ObraVersaoEvento.versao_id
    ).where(ObraVersao.obra_id == obra.id).order_by(ObraVersaoEvento.id)).all()
    pendentes = {}
    for evento in eventos:
        if evento.tipo == "revisao_solicitada":
            pendentes[evento.id] = evento
        elif evento.tipo in {"solicitacao_aceita", "solicitacao_dispensada"}:
            pendentes.pop(json.loads(evento.detalhe)["solicitacao_id"], None)
    return next(iter(pendentes.values()), None)


def solicitar_revisao(sessao, versao, revisor: User, motivo: str) -> ObraVersaoEvento:
    _autor(revisor, Role.REVISOR)
    obra, versao = _estado(sessao, versao, "liberada")
    if not isinstance(motivo, str) or not motivo.strip():
        raise FluxoBloqueado("Motivo obrigatorio")
    if obra.versao_liberada_id != versao.id or _solicitacao_pendente(sessao, obra):
        raise FluxoBloqueado("Versao nao vigente ou solicitacao ja pendente")
    return _evento(sessao, versao, "revisao_solicitada", revisor, motivo=motivo)


def aceitar_solicitacao(sessao, obra, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra = _obra(sessao, obra.id)
    pedido = _solicitacao_pendente(sessao, obra)
    if pedido is None:
        raise FluxoBloqueado("Nenhuma solicitacao pendente")
    nova = _nova_versao(sessao, obra, admin)
    _suspender(sessao, obra)
    _evento(sessao, nova, "solicitacao_aceita", admin, solicitacao_id=pedido.id,
            versao_anterior_id=pedido.versao_id)
    return nova


def dispensar_solicitacao(sessao, obra, admin: User, motivo: str) -> ObraVersaoEvento:
    _autor(admin, Role.ADMIN)
    if not isinstance(motivo, str) or not motivo.strip():
        raise FluxoBloqueado("Motivo da dispensa obrigatorio")
    obra = _obra(sessao, obra.id)
    pedido = _solicitacao_pendente(sessao, obra)
    if pedido is None:
        raise FluxoBloqueado("Nenhuma solicitacao pendente")
    return _evento(sessao, sessao.get(ObraVersao, pedido.versao_id), "solicitacao_dispensada",
                   admin, solicitacao_id=pedido.id, motivo=motivo)


def cancelar_ciclo(sessao, obra, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra = _obra(sessao, obra.id)
    if obra.versao_liberada_id is None:
        raise FluxoBloqueado("Obra sem versao liberada para retomar")
    pendentes = sessao.exec(select(ObraVersao).where(
        ObraVersao.obra_id == obra.id,
        ObraVersao.status.in_(["em_revisao", "aguardando_admin", "devolvida"]),
    )).all()
    if len(pendentes) != 1:
        raise FluxoBloqueado("Nenhum ciclo unico para cancelar")
    versao = pendentes[0]
    # Cancelamento logico preserva as evidencias e impede liberar o ciclo descartado.
    versao.status = "cancelada"
    obra.status = "liberada"
    obra.disponibilidade = "aberta"
    obra.updated_at = _agora()
    sessao.add_all([obra, versao])
    _evento(sessao, versao, "ciclo_cancelado", admin)
    return versao


def posicionar(sessao, versao, revisor: User, posicao: str, texto: str) -> ObraVersaoEvento:
    _autor(revisor, Role.REVISOR)
    _obra(sessao, versao.obra_id)
    versao = sessao.get(ObraVersao, versao.id, populate_existing=True)
    if versao is None or posicao not in {"concordo", "objeto"} or not isinstance(texto, str) or not texto.strip():
        raise FluxoBloqueado("Posicao ou texto invalido")
    return _evento(sessao, versao, "posicao", revisor, posicao=posicao, texto=texto)


def vincular(sessao, ambiente: Ambiente, obra: Obra, coordenador: User) -> VinculoObra:
    _autor(coordenador, Role.COORDENADOR)
    ambiente = sessao.get(Ambiente, ambiente.id)
    if ambiente is None or ambiente.coordenador_id != coordenador.id:
        raise FluxoBloqueado("Ambiente fora do escopo do coordenador")
    obra = _obra(sessao, obra.id)
    if obra.disponibilidade != "aberta" or obra.versao_liberada_id is None:
        raise FluxoBloqueado("Obra indisponivel para novas vinculacoes")
    versao = sessao.get(ObraVersao, obra.versao_liberada_id)
    if versao.status != "liberada":
        raise FluxoBloqueado("Versao nao liberada")
    vinculo = VinculoObra(ambiente_id=ambiente.id, obra_id=obra.id, versao_id=versao.id,
                         coordenador_id=coordenador.id, created_at=_agora())
    sessao.add(vinculo)
    sessao.flush()
    return vinculo


def diferenca(sessao, versao, atual: bool = False) -> list[dict]:
    def itens(momento):
        capitulos = sessao.exec(select(ObraVersaoCapitulo).where(
            ObraVersaoCapitulo.versao_id == versao.id,
            ObraVersaoCapitulo.momento == momento,
            ObraVersaoCapitulo.rodada == versao.rodada,
        )).all()
        adendos = sessao.exec(select(ObraVersaoAdendo).where(
            ObraVersaoAdendo.versao_id == versao.id,
            ObraVersaoAdendo.momento == momento,
            ObraVersaoAdendo.rodada == versao.rodada,
        )).all()
        return capitulos, adendos

    def mapa(capitulos, adendos):
        return {
            **{f"capitulo:{c.ordem}": {"hash": hash_capitulo(c), "titulo": c.titulo,
                                      "texto": c.conteudo_md} for c in capitulos},
            **{f"adendo:{_normalizar(a.codigo)}": {"hash": hash_adendo(a), "titulo": a.titulo,
                                     "texto": a.texto} for a in adendos},
        }

    visto = mapa(*itens("visto"))
    liberado = mapa(*(_trabalho(sessao, versao.obra_id) if atual else itens("liberado")))
    return [{"item": chave, "visto": visto.get(chave), "liberado": liberado.get(chave)}
            for chave in sorted(visto.keys() | liberado.keys())
            if visto.get(chave) != liberado.get(chave)]
