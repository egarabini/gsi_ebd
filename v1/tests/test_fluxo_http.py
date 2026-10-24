import json
import re

from sqlmodel import Session, select

from gsi_ebd.models import Obra, ObraCapitulo, ObraVersao, ObraVersaoCapitulo, ObraVersaoEvento, Role
from v1.tests.conftest import entrar, payload


def test_rf06_rf12_fluxo_admin_revisor_pela_tela(sistema):
    c = sistema["client"]
    token = entrar(c, Role.ADMIN)
    dados = payload(sistema, token)
    dados.pop("versao_id")
    r = c.post("/admin/obras", data=dados, follow_redirects=False)
    assert r.status_code == 303, r.text
    obra_id = int(r.headers["location"].rsplit("/", 1)[1])
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    detalhe = c.get(f"/revisor/obras/{obra_id}")
    esperado = re.search(r'name="hash_esperado" value="([^"]+)"', detalhe.text).group(1)
    with Session(sistema["engine"]) as session:
        primeira_id = session.exec(select(ObraVersao).where(ObraVersao.obra_id == obra_id)).one().id
    dados = {
        "csrf_token": token,
        "versao_id": primeira_id,
        "hash_esperado": esperado,
        "parecer": "Conferido",
        "ajustes": "Melhorar nota",
    }
    assert c.post(f"/revisor/obras/{obra_id}/revisar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, obra_id).versao_liberada_id is None
        assert session.get(ObraVersao, primeira_id).status == "aguardando_admin"
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    dados = payload(sistema, token)
    dados["versao_id"] = str(primeira_id)
    dados["capitulo_texto"] = "Texto liberado"
    assert c.post(f"/admin/obras/{obra_id}/liberar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, obra_id)
        assert obra.versao_liberada_id == primeira_id and obra.disponibilidade == "aberta"
        primeira = session.get(ObraVersao, primeira_id)
        assert primeira.hash_visto != primeira.hash_liberado
    dados["capitulo_texto"] = "Nova versao proposta"
    assert c.post(f"/admin/obras/{obra_id}/alterar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, obra_id)
        assert obra.disponibilidade == "suspensa_para_novos" and obra.versao_liberada_id == primeira_id
        assert session.get(ObraVersao, primeira_id).status == "liberada"
        original = session.exec(
            select(ObraVersaoCapitulo).where(
                ObraVersaoCapitulo.versao_id == primeira_id,
                ObraVersaoCapitulo.momento == "liberado",
            )
        ).one()
        assert original.conteudo_md == "Texto liberado"
    html = c.get(f"/obras/{obra_id}").text
    assert "Texto liberado" in html and "Nova versao proposta" in html


def test_rf03_hash_desatualizado_sem_sucesso_falso(sistema):
    c = sistema["client"]
    token = entrar(c, Role.REVISOR)
    dados = payload(sistema, token)
    with Session(sistema["engine"]) as session:
        cap = session.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == sistema["obra_id"])).one()
        cap.conteudo_md = "Mudou apos abrir a tela"
        session.add(cap)
        session.commit()
    r = c.post(f'/revisor/obras/{sistema["obra_id"]}/revisar', data=dados, follow_redirects=False)
    assert r.status_code == 409 and "mudou desde que voce abriu" in r.text
    with Session(sistema["engine"]) as session:
        assert session.get(ObraVersao, sistema["versao_id"]).status == "em_revisao"
        assert not session.exec(select(ObraVersaoEvento).where(ObraVersaoEvento.tipo == "vista")).all()


def test_rf07_gate_importacao_sem_obra_parcial(sistema):
    c = sistema["client"]
    dados = payload(sistema, entrar(c, Role.ADMIN))
    dados["fonte_id"] = "F-003"
    r = c.post("/admin/obras", data=dados, follow_redirects=False)
    assert r.status_code == 409 and "fonte nao entra" in r.text
    with Session(sistema["engine"]) as session:
        assert len(session.exec(select(Obra)).all()) == 1


def test_rf07_liberacao_bloqueada_reverte_ajustes(sistema):
    c = sistema["client"]
    token = entrar(c, Role.REVISOR)
    c.post(f'/revisor/obras/{sistema["obra_id"]}/revisar', data=payload(sistema, token))
    c.post("/logout", data={"csrf_token": token})
    dados = payload(sistema, entrar(c, Role.ADMIN))
    dados["capitulo_texto"] = "Ajuste que deve ser revertido"
    sistema["inventario"].write_text("id;decisao\nF-001;depende\n", encoding="utf-8")
    r = c.post(f'/admin/obras/{sistema["obra_id"]}/liberar', data=dados, follow_redirects=False)
    assert r.status_code == 409
    with Session(sistema["engine"]) as session:
        assert session.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == sistema["obra_id"])).one().conteudo_md == "Texto inicial"
        assert session.get(Obra, sistema["obra_id"]).versao_liberada_id is None


def test_rf01_render_escapa_conteudo(sistema):
    c = sistema["client"]
    entrar(c, Role.ADMIN)
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, sistema["obra_id"])
        obra.titulo = '<script>alert("xss")</script>'
        session.add(obra)
        session.commit()
    r = c.get(f'/admin/obras/{sistema["obra_id"]}')
    assert r.status_code == 200 and '<script>alert("xss")</script>' not in r.text and "&lt;script&gt;" in r.text


def test_rf06_rf12_solicitacao_aceite_posicao_cancelamento_e_dispensa_http(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    assert c.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/solicitar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, oid).disponibilidade == "aberta"
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    assert c.post(f"/admin/obras/{oid}/aceitar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        assert obra.disponibilidade == "suspensa_para_novos" and obra.versao_liberada_id == sistema["versao_id"]
        nova = session.exec(select(ObraVersao).where(ObraVersao.obra_id == oid, ObraVersao.numero == 2)).one()
        nid = nova.id
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    dados = payload(sistema, token)
    dados["versao_id"] = str(nid)
    assert c.post(f"/revisor/obras/{oid}/posicionar", data=dados, follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    dados["csrf_token"] = token
    assert c.post(f"/admin/obras/{oid}/cancelar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        assert session.get(Obra, oid).disponibilidade == "aberta"
        assert session.get(ObraVersao, nid).status == "cancelada"
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    dados["csrf_token"], dados["versao_id"] = token, str(sistema["versao_id"])
    assert c.post(f"/revisor/obras/{oid}/solicitar", data=dados, follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    dados.update({"csrf_token": token, "versao_id": str(nid), "motivo": ""})
    assert c.post(f"/admin/obras/{oid}/dispensar", data=dados, follow_redirects=False).status_code == 409
    dados["motivo"] = "Ja atendido na versao publicada"
    assert c.post(f"/admin/obras/{oid}/dispensar", data=dados, follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        evento = session.exec(select(ObraVersaoEvento).where(ObraVersaoEvento.tipo == "solicitacao_dispensada")).one()
        assert json.loads(evento.detalhe)["motivo"] == dados["motivo"]
    c.post("/logout", data={"csrf_token": token})
    entrar(c, Role.REVISOR)
    assert "Ja atendido na versao publicada" in c.get(f"/revisor/obras/{oid}").text


def test_rf07_recusa_reenvio_rodada2_http(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/recusar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    dados = payload(sistema, token)
    dados["capitulo_texto"] = "Texto corrigido pelo admin"
    assert c.post(f"/admin/obras/{oid}/reenviar", data=dados, follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    with Session(sistema["engine"]) as session:
        versao = session.get(ObraVersao, sistema["versao_id"])
        assert versao.status == "aguardando_admin" and versao.rodada == 1
