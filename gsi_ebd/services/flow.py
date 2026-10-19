"""Fluxo editorial da obra; a transacao pertence ao chamador."""
from collections.abc import Mapping
from hashlib import sha256
from datetime import datetime, timezone
import json
import unicodedata

from sqlmodel import Session, select

from gsi_ebd.models import (
    Adendo, Obra, ObraCapitulo, ObraVersao, ObraVersaoAdendo,
    ObraVersaoCapitulo, ObraVersaoEvento, Role, User,
)
from gsi_ebd.services.fontes import fonte_decisao


class FluxoBloqueado(ValueError):
    pass


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
    if atual is None or atual.status != esperado:
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
            versao_id=versao.id, momento=momento, ordem=capitulo.ordem,
            titulo=capitulo.titulo, conteudo_md=capitulo.conteudo_md,
            item_hash=hash_capitulo(capitulo),
        ))
    for adendo in adendos:
        sessao.add(ObraVersaoAdendo(
            versao_id=versao.id, momento=momento, codigo=adendo.codigo,
            titulo=adendo.titulo, texto=adendo.texto, item_hash=hash_adendo(adendo),
        ))


def _hash_itens(capitulos, adendos):
    return hash_canonico({
        **{f"capitulo:{c.ordem}": hash_capitulo(c) for c in capitulos},
        **{f"adendo:{_normalizar(a.codigo)}": hash_adendo(a) for a in adendos},
    })


def _evento(sessao, versao, tipo, autor, **detalhe):
    sessao.add(ObraVersaoEvento(
        versao_id=versao.id, tipo=tipo, autor_id=autor.id, quando=_agora(),
        detalhe=json.dumps({"hash": versao.conteudo_hash, **detalhe}, ensure_ascii=True),
    ))
    sessao.flush()


def _publicar_estado(sessao, obra, versao):
    if obra.versao_liberada_id is None:
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
    if fonte_decisao(fonte) == "nao_entra":
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
    obra, versao = _estado(sessao, versao, "em_revisao")
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
    obra.status = "liberada"
    obra.versao_liberada_id = versao.id
    _publicar_estado(sessao, obra, versao)
    _evento(sessao, versao, "liberada", admin, ajustes=ajustes_descritos,
            hash_visto=versao.hash_visto, hash_liberado=versao.hash_liberado)
    return versao


def alterar(sessao, obra, conteudo: dict, admin: User) -> ObraVersao:
    _autor(admin, Role.ADMIN)
    obra = _obra(sessao, obra.id)
    if obra.versao_liberada_id is None:
        raise FluxoBloqueado("Obra ainda nao liberada")
    # Valida todo o conteudo antes de modificar a copia de trabalho.
    capitulos = [ObraCapitulo.model_validate({
        "obra_id": obra.id, "ordem": item["ordem"], "titulo": item.get("titulo", ""),
        "conteudo_md": item.get("conteudo_md", ""),
    }) for item in conteudo["capitulos"]]
    adendos = [Adendo.model_validate({
        "obra_id": obra.id, "autor_id": admin.id, "codigo": item["codigo"],
        "titulo": item.get("titulo", ""), "texto": item.get("texto", ""),
        "ambiente_id": item.get("ambiente_id"),
    }) for item in conteudo["adendos"]]
    if any(a.ambiente_id is not None for a in adendos):
        raise FluxoBloqueado("Alterar recebe somente adendos da base")
    if len({c.ordem for c in capitulos}) != len(capitulos) or len({_normalizar(a.codigo) for a in adendos}) != len(adendos):
        raise FluxoBloqueado("Itens duplicados")
    versao = _nova_versao(sessao, obra, admin)
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


def contestar(sessao, versao, revisor: User) -> ObraVersao:
    _autor(revisor, Role.REVISOR)
    obra, versao = _estado(sessao, versao, "liberada")
    if obra.versao_liberada_id != versao.id:
        raise FluxoBloqueado("Conteste a versao publicada atual")
    # A assinatura e os instantaneos publicados permanecem como evidencia.
    nova = _nova_versao(sessao, obra, revisor)
    _evento(sessao, nova, "contestada", revisor, versao_anterior_id=versao.id)
    return nova


def diferenca(sessao, versao, atual: bool = False) -> list[dict]:
    def itens(momento):
        capitulos = sessao.exec(select(ObraVersaoCapitulo).where(
            ObraVersaoCapitulo.versao_id == versao.id,
            ObraVersaoCapitulo.momento == momento,
        )).all()
        adendos = sessao.exec(select(ObraVersaoAdendo).where(
            ObraVersaoAdendo.versao_id == versao.id,
            ObraVersaoAdendo.momento == momento,
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
