"""Regras de autoridade da ADR-020 exercitadas pelas telas e pelo hash."""
import pytest
from sqlmodel import Session, select

from gsi_ebd.models import (
    Ambiente,
    Obra,
    ObraCapitulo,
    ObraVersao,
    ObraVersaoCapitulo,
    Role,
    User,
)
from gsi_ebd.services import flow
from gsi_ebd.services.erros_fluxo import FluxoBloqueado
from v1.tests.conftest import entrar, payload


def test_so_admin_muda_publicacao_revisor_leva_403(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    dados = payload(sistema, token)
    for acao in ("liberar", "alterar", "cancelar", "aceitar", "dispensar"):
        r = c.post(f"/admin/obras/{oid}/{acao}", data=dados, follow_redirects=False)
        assert r.status_code == 403, acao


def test_admin_nao_assina_parecer_nem_move_editorial(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.ADMIN)
    dados = payload(sistema, token)
    for acao in ("revisar", "recusar", "solicitar", "posicionar"):
        r = c.post(f"/revisor/obras/{oid}/{acao}", data=dados, follow_redirects=False)
        assert r.status_code == 403, acao


def test_liberacao_exige_assinatura_do_revisor_e_do_admin(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.ADMIN)
    r = c.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False)
    assert r.status_code == 409
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, oid).versao_liberada_id is None
        assert session.get(ObraVersao, sistema["versao_id"]).status == "em_revisao"
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, oid).versao_liberada_id is None
        assert session.get(ObraVersao, sistema["versao_id"]).status == "aguardando_admin"
        assert session.get(ObraVersao, sistema["versao_id"]).revisor_id is not None
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    assert c.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        versao = session.get(ObraVersao, sistema["versao_id"])
        assert obra.versao_liberada_id == versao.id
        assert obra.disponibilidade == "aberta"
        assert versao.status == "liberada"


def test_versao_liberada_e_imutavel_ciclo_cria_n_mais_1(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token))
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    dados = payload(sistema, token)
    dados["capitulo_texto"] = "Texto congelado"
    assert c.post(f"/admin/obras/{oid}/liberar", data=dados, follow_redirects=False).status_code == 303
    dados["capitulo_texto"] = "Texto da N+1"
    assert c.post(f"/admin/obras/{oid}/alterar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        n = session.get(ObraVersao, sistema["versao_id"])
        n1 = session.exec(select(ObraVersao).where(ObraVersao.obra_id == oid, ObraVersao.numero == 2)).one()
        snapshot = session.exec(
            select(ObraVersaoCapitulo).where(
                ObraVersaoCapitulo.versao_id == n.id,
                ObraVersaoCapitulo.momento == "liberado",
            )
        ).one()
        assert snapshot.conteudo_md == "Texto congelado"
        assert n.status == "liberada"
        assert n1.numero == 2 and n1.status == "em_revisao"
        assert obra.versao_liberada_id == n.id
        assert obra.disponibilidade == "suspensa_para_novos"


@pytest.mark.parametrize(
    "texto,equivalente",
    [("A\nB\nC", "A\r\nB\rC"), ("Caf\u00e9", "Cafe\u0301")],
)
def test_hash_canonico_lf_nfc(texto, equivalente):
    cap_a = ObraCapitulo(obra_id=1, ordem=1, titulo="Titulo", conteudo_md=texto)
    cap_b = ObraCapitulo(obra_id=1, ordem=1, titulo="Titulo", conteudo_md=equivalente)
    assert flow.hash_capitulo(cap_a) == flow.hash_capitulo(cap_b)
    assert flow.hash_canonico({"capitulo:1": flow.hash_capitulo(cap_a)}) == flow.hash_canonico(
        {"capitulo:1": flow.hash_capitulo(cap_b)}
    )


def test_disponibilidade_aberta_ou_suspensa_para_novos(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token))
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    assert c.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, oid).disponibilidade == "aberta"
        coord = session.exec(select(User).where(User.role == int(Role.COORDENADOR))).one()
        ambiente = Ambiente(nome="Sala teste", slug="sala-teste", coordenador_id=coord.id)
        session.add(ambiente)
        session.commit()
        session.refresh(ambiente)
        flow.vincular(session, ambiente, session.get(Obra, oid), coord)
        session.commit()
    dados = payload(sistema, token)
    dados["capitulo_texto"] = "Ciclo novo"
    assert c.post(f"/admin/obras/{oid}/alterar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        assert obra.disponibilidade == "suspensa_para_novos"
        coord = session.exec(select(User).where(User.role == int(Role.COORDENADOR))).one()
        ambiente = session.exec(select(Ambiente).where(Ambiente.slug == "sala-teste")).one()
        with pytest.raises(FluxoBloqueado):
            flow.vincular(session, ambiente, obra, coord)
