"""DEM-011: C-02/C-03 e primitivas de permissao RF02."""
from hashlib import sha256

import pytest
from sqlmodel import Session, SQLModel, create_engine

from gsi_ebd.models import Adendo, Obra, ObraCapitulo, Role, User
from gsi_ebd.services.flow import (
    FluxoBloqueado, exigir_papel, hash_adendo, hash_capitulo,
    hash_canonico, hash_obra, tamanho_diferenca,
)


def test_rf03_c02_vetor_canonico_v4():
    capitulo = ObraCapitulo(obra_id=1, ordem=2, titulo="Titulo", conteudo_md="Linha\nTexto")
    adendo = Adendo(obra_id=1, codigo="ADO-01", titulo="Nota", texto="Texto")
    cap_hash = sha256(b'{"conteudo_md":"Linha\\nTexto","ordem":2,"titulo":"Titulo"}').hexdigest()
    ad_hash = sha256(b'{"codigo":"ADO-01","texto":"Texto","titulo":"Nota"}').hexdigest()
    esperado = sha256((f"v1\nadendo:ADO-01\t{ad_hash}\ncapitulo:2\t{cap_hash}").encode()).hexdigest()
    assert hash_capitulo(capitulo) == cap_hash
    assert hash_adendo(adendo) == ad_hash
    assert hash_canonico({"capitulo:2": cap_hash, "adendo:ADO-01": ad_hash}) == esperado
    assert hash_canonico({"adendo:ADO-01": ad_hash, "capitulo:2": cap_hash}) == esperado
    assert hash_canonico({}) == sha256(b"v1\n").hexdigest()


@pytest.mark.parametrize("campo,valor", [("ordem", 3), ("titulo", "Outro"), ("conteudo_md", "Novo")])
def test_rf03_c02_capitulo_alterado_muda_hash(campo, valor):
    capitulo = ObraCapitulo(obra_id=1, ordem=1, titulo="Titulo", conteudo_md="Texto")
    antes = hash_capitulo(capitulo)
    setattr(capitulo, campo, valor)
    assert hash_capitulo(capitulo) != antes


@pytest.mark.parametrize("campo,valor", [("codigo", "ADO-02"), ("titulo", "Outra"), ("texto", "Novo")])
def test_rf03_c02_adendo_alterado_muda_hash(campo, valor):
    adendo = Adendo(obra_id=1, codigo="ADO-01", titulo="Nota", texto="Texto")
    antes = hash_adendo(adendo)
    setattr(adendo, campo, valor)
    assert hash_adendo(adendo) != antes


def test_rf11_c03_diferenca_conta_alterados_incluidos_e_removidos():
    assert tamanho_diferenca({"a": "1", "b": "2", "c": "3"},
                             {"a": "1", "b": "4", "d": "5"}) == 3
    assert tamanho_diferenca({"a": "1"}, {"a": "1"}) == 0
    assert tamanho_diferenca({}, {}) == 0


def test_rf03_c02_hash_obra_exclui_adendo_ambiente_e_outra_obra():
    engine = create_engine("sqlite://")
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as sessao:
            obra = Obra(titulo="Base")
            outra = Obra(titulo="Outra")
            sessao.add_all([obra, outra])
            sessao.flush()
            capitulo = ObraCapitulo(obra_id=obra.id, ordem=1, titulo="Titulo", conteudo_md="Texto")
            adendo = Adendo(obra_id=obra.id, codigo="ADO-01", texto="Base")
            sessao.add_all([capitulo, adendo])
            sessao.flush()
            esperado = hash_canonico({"capitulo:1": hash_capitulo(capitulo), "adendo:ADO-01": hash_adendo(adendo)})
            assert hash_obra(sessao, obra.id) == esperado
            sessao.add_all([
                Adendo(obra_id=obra.id, ambiente_id=123, codigo="ADO-02", texto="Ambiente"),
                ObraCapitulo(obra_id=outra.id, ordem=1, conteudo_md="Outro"),
            ])
            sessao.flush()
            assert hash_obra(sessao, obra.id) == esperado
            capitulo.conteudo_md = "Alterado"
            sessao.add(capitulo)
            sessao.flush()
            assert hash_obra(sessao, obra.id) != esperado
    finally:
        engine.dispose()


@pytest.mark.parametrize("exigido", [Role.ADMIN, Role.REVISOR])
@pytest.mark.parametrize("recebido", list(Role))
def test_rf02_primitiva_de_permissao_exige_papel_exato(exigido, recebido):
    usuario = User(email="papel@example.test", role=recebido)
    if recebido == exigido:
        exigir_papel(usuario, exigido)
    else:
        with pytest.raises(FluxoBloqueado, match="Papel"):
            exigir_papel(usuario, exigido)


@pytest.fixture
def fluxo(tmp_path, monkeypatch):
    from gsi_ebd.services import fontes, flow
    inventario = tmp_path / "fontes.csv"
    inventario.write_text("id;decisao\nF-001;entra\nF-002;depende\nF-003;nao_entra\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(inventario))
    fontes._carregar.cache_clear()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as sessao:
            admin = User(email="admin@example.test", role=Role.ADMIN)
            revisor = User(email="revisor@example.test", role=Role.REVISOR)
            sessao.add_all([admin, revisor])
            sessao.flush()
            yield sessao, flow, admin, revisor, inventario
    finally:
        engine.dispose()
        fontes._carregar.cache_clear()


def preparar(fluxo, fonte="F-001"):
    sessao, flow, admin, revisor, _ = fluxo
    obra = Obra(titulo="Obra")
    versao = flow.importar(sessao, fonte, obra, admin)
    sessao.add_all([
        ObraCapitulo(obra_id=obra.id, ordem=1, titulo="Um", conteudo_md="Original"),
        Adendo(obra_id=obra.id, codigo="ADO-01", titulo="Nota", texto="Base"),
    ])
    sessao.flush()
    return obra, versao


def aprovar(fluxo, versao):
    sessao, flow, _, revisor, _ = fluxo
    return flow.revisar(sessao, versao, "Aprovado", ["Ajustar nota"], revisor,
                        flow.hash_obra(sessao, versao.obra_id))


def novo_conteudo():
    return {"capitulos": [{"ordem": 1, "titulo": "Novo", "conteudo_md": "Alterado"}],
            "adendos": [{"codigo": "ADO-01", "titulo": "Nota", "texto": "Nova base"}]}


def test_rf01_f01_f02_f04_h14_jornada(fluxo):
    import json
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    assert obra.status == versao.status == "em_revisao"
    assert versao.numero == 1
    assert obra.fonte_id == "F-001"
    aprovar(fluxo, versao)
    assert obra.status == versao.status == "aguardando_admin"
    assert versao.revisor_id == revisor.id and versao.revisado_em
    assert versao.parecer == "Aprovado"
    assert json.loads(versao.ajustes_propostos) == ["Ajustar nota"]
    assert versao.hash_visto == flow.hash_obra(sessao, obra.id)
    flow.liberar(sessao, versao, "Sem ajustes necessarios", admin)
    assert obra.status == versao.status == "liberada"
    assert obra.versao_liberada_id == versao.id
    assert versao.admin_id == admin.id and versao.liberada_em
    assert versao.hash_visto == versao.hash_liberado
    sessao.commit()
    sessao.expire_all()
    assert sessao.get(Obra, obra.id).fonte_id == "F-001"


def test_rf01_f03_f07_recusa_e_reenvio(fluxo):
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    flow.recusar(sessao, versao, "Rever texto", revisor, flow.hash_obra(sessao, obra.id))
    assert obra.status == versao.status == "devolvida"
    with pytest.raises(FluxoBloqueado):
        flow.liberar(sessao, versao, "Ajustado", admin)
    flow.reenviar(sessao, versao, "Texto corrigido", admin)
    assert obra.status == versao.status == "em_revisao"
    assert versao.ajustes_descritos == "Texto corrigido"
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Concluido", admin)
    assert versao.status == "liberada"


def test_rf05_f05_f09_n07_snapshot_liberada_imutavel(fluxo):
    from gsi_ebd.models import ObraVersaoCapitulo, ObraVersaoAdendo
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Sem alteracao", admin)
    capitulos = sessao.exec(select(ObraVersaoCapitulo).where(
        ObraVersaoCapitulo.versao_id == versao.id, ObraVersaoCapitulo.momento == "liberado")).all()
    notas = sessao.exec(select(ObraVersaoAdendo).where(
        ObraVersaoAdendo.versao_id == versao.id, ObraVersaoAdendo.momento == "liberado")).all()
    assert len(capitulos) == len(notas) == 1
    original = versao.hash_liberado
    nova = flow.alterar(sessao, obra, novo_conteudo(), admin)
    sessao.commit()
    sessao.expire_all()
    assert capitulos[0].conteudo_md == "Original"
    assert notas[0].texto == "Base"
    assert versao.hash_liberado == original
    assert obra.versao_liberada_id == versao.id
    assert versao.status == "liberada" and obra.status == "em_revisao"
    assert nova.numero == 2 and nova.status == "em_revisao"
    assert nova.conteudo_hash == flow.hash_obra(sessao, obra.id) != original


@pytest.mark.parametrize("papel", [p for p in Role if p != Role.ADMIN])
def test_rf11_f06_solicitacao_nao_abre_ciclo_e_so_admin_altera(fluxo, papel):
    from gsi_ebd.models import ObraVersao, ObraVersaoCapitulo, ObraVersaoAdendo
    from sqlmodel import select
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Inicial", admin)
    sessao.commit()
    sessao.refresh(versao)
    anterior = versao.model_dump()
    caps = [c.model_dump() for c in sessao.exec(select(ObraVersaoCapitulo)).all()]
    notas = [a.model_dump() for a in sessao.exec(select(ObraVersaoAdendo)).all()]
    pedido = flow.solicitar_revisao(sessao, versao, revisor, "Reavaliar a fonte")
    assert pedido.tipo == "revisao_solicitada" and pedido.versao_id == versao.id
    assert obra.disponibilidade == "aberta" and obra.status == "liberada"
    assert obra.versao_liberada_id == versao.id
    assert len(sessao.exec(select(ObraVersao)).all()) == 1
    usuario = User(id=123, email="outro@example.test", role=papel)
    with pytest.raises(FluxoBloqueado, match="Papel"):
        flow.alterar(sessao, obra, novo_conteudo(), usuario)
    nova = flow.alterar(sessao, obra, novo_conteudo(), admin)
    sessao.commit()
    sessao.expire_all()
    assert nova.id != versao.id and nova.numero == 2 and nova.status == "em_revisao"
    assert obra.disponibilidade == "suspensa_para_novos"
    assert obra.versao_liberada_id == versao.id
    assert versao.model_dump() == anterior
    assert [c.model_dump() for c in sessao.exec(select(ObraVersaoCapitulo)).all()] == caps
    assert [a.model_dump() for a in sessao.exec(select(ObraVersaoAdendo)).all()] == notas
    aprovar(fluxo, nova)
    assert nova.status == "aguardando_admin"
    assert obra.versao_liberada_id == versao.id
    assert obra.disponibilidade == "suspensa_para_novos"
    flow.recusar(sessao, nova, "Rever o parecer", revisor, hash_obra(sessao, obra.id))
    assert nova.status == "devolvida"
    assert obra.versao_liberada_id == versao.id
    assert obra.disponibilidade == "suspensa_para_novos"
    assert versao.model_dump() == anterior
    assert not hasattr(flow, "contestar")


def test_rf11_f08_c01_c04_c06_diferenca_mostra_texto(fluxo):
    from gsi_ebd.models import ObraVersaoCapitulo
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    visto = sessao.exec(select(ObraVersaoCapitulo).where(
        ObraVersaoCapitulo.versao_id == versao.id,
        ObraVersaoCapitulo.momento == "visto")).one()
    assert visto.conteudo_md == "Original"
    capitulo = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).one()
    capitulo.conteudo_md = "Ajustado"
    sessao.add(capitulo)
    sessao.flush()
    previa = flow.diferenca(sessao, versao, atual=True)
    assert len(previa) == 1
    assert previa[0]["item"] == "capitulo:1"
    assert previa[0]["visto"]["texto"] == "Original"
    assert previa[0]["liberado"]["texto"] == "Ajustado"
    flow.liberar(sessao, versao, "Texto ajustado", admin)
    assert versao.hash_visto != versao.hash_liberado
    assert flow.diferenca(sessao, versao) == previa
    capitulo.conteudo_md = "Edicao posterior"
    sessao.add(capitulo)
    sessao.flush()
    assert flow.diferenca(sessao, versao) == previa


def test_rf07_n01_nao_entra_nao_cria_obra(fluxo):
    from sqlmodel import select
    from gsi_ebd.models import ObraVersao
    sessao, flow, admin, _, _ = fluxo
    with pytest.raises(FluxoBloqueado, match="fonte"):
        flow.importar(sessao, "F-003", Obra(titulo="Proibida"), admin)
    assert sessao.exec(select(Obra)).all() == []
    assert sessao.exec(select(ObraVersao)).all() == []


def test_rf07_n02_depende_importa_mas_nao_libera(fluxo):
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo, "F-002")
    aprovar(fluxo, versao)
    with pytest.raises(FluxoBloqueado, match="fonte"):
        flow.liberar(sessao, versao, "Concluido", admin)
    assert versao.status == "aguardando_admin" and obra.versao_liberada_id is None


@pytest.mark.parametrize("campo,valor", [("revisor_id", None), ("revisado_em", None), ("hash_visto", "")])
def test_rf03_n03_assinatura_incompleta_bloqueia(fluxo, campo, valor):
    sessao, flow, admin, _, _ = fluxo
    _, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    setattr(versao, campo, valor)
    sessao.add(versao)
    sessao.flush()
    with pytest.raises(FluxoBloqueado, match="Assinatura"):
        flow.liberar(sessao, versao, "Ajustado", admin)
    assert versao.status == "aguardando_admin"


@pytest.mark.parametrize("papel", [p for p in Role if p != Role.REVISOR])
@pytest.mark.parametrize("operacao", ["revisar", "recusar"])
def test_rf02_n04_papel_incorreto_na_revisao(fluxo, papel, operacao):
    sessao, flow, _, _, _ = fluxo
    obra, versao = preparar(fluxo)
    usuario = User(id=123, email="outro@example.test", role=papel)
    argumentos = [sessao, versao, "Parecer"]
    if operacao == "revisar":
        argumentos.append([])
    with pytest.raises(FluxoBloqueado, match="Papel"):
        getattr(flow, operacao)(*argumentos, usuario, flow.hash_obra(sessao, obra.id))
    assert versao.status == "em_revisao"


@pytest.mark.parametrize("papel", [p for p in Role if p != Role.ADMIN])
@pytest.mark.parametrize("operacao", ["importar", "liberar", "alterar"])
def test_rf02_n05_papel_incorreto_na_administracao(fluxo, papel, operacao):
    sessao, flow, _, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    usuario = User(id=123, email="outro@example.test", role=papel)
    argumentos = {"importar": [sessao, "F-001", Obra(titulo="Outra"), usuario],
                  "liberar": [sessao, versao, "Ajustado", usuario],
                  "alterar": [sessao, obra, novo_conteudo(), usuario]}
    with pytest.raises(FluxoBloqueado, match="Papel"):
        getattr(flow, operacao)(*argumentos[operacao])


def test_rf01_n06_transicao_invalida(fluxo):
    sessao, flow, admin, _, _ = fluxo
    _, versao = preparar(fluxo)
    with pytest.raises(FluxoBloqueado, match="Transicao"):
        flow.liberar(sessao, versao, "Ajustado", admin)


@pytest.mark.parametrize("operacao", ["revisar", "recusar"])
def test_rf03_n08_hash_esperado_impede_assinar_conteudo_nao_visto(fluxo, operacao):
    from sqlmodel import select
    sessao, flow, _, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    esperado = flow.hash_obra(sessao, obra.id)
    capitulo = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).one()
    capitulo.conteudo_md = "Mudou antes do parecer"
    sessao.add(capitulo)
    sessao.flush()
    argumentos = [sessao, versao, "Parecer"]
    if operacao == "revisar":
        argumentos.append([])
    with pytest.raises(FluxoBloqueado, match="mudou"):
        getattr(flow, operacao)(*argumentos, revisor, esperado)
    assert versao.status == "em_revisao" and not versao.hash_visto


def test_rf07_c05_consulta_fonte_persistida_na_liberacao(fluxo, monkeypatch):
    from gsi_ebd.services import fontes
    sessao, flow, admin, _, inventario = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    sessao.commit()
    sessao.expire_all()
    atualizado = inventario.parent / "inventario-atual.csv"
    atualizado.write_text("id;decisao\nF-001;depende\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(atualizado))
    with pytest.raises(FluxoBloqueado, match="fonte"):
        flow.liberar(sessao, versao, "Ajustado", admin)
    atualizado.write_text("id;decisao\nF-001;entra\n", encoding="utf-8")
    fontes._carregar.cache_clear()
    flow.liberar(sessao, versao, "Concluido", admin)
    assert obra.fonte_id == "F-001" and versao.status == "liberada"


def test_rf03_c07_flow_nao_importa_reflex():
    import ast
    from pathlib import Path
    from gsi_ebd.services import flow
    arvore = ast.parse(Path(flow.__file__).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            assert all(n.name.split(".")[0] != "reflex" for n in no.names)
        if isinstance(no, ast.ImportFrom):
            assert (no.module or "").split(".")[0] != "reflex"


@pytest.mark.parametrize("trecho", ["|", '|"\n'])
def test_rf03_c08_json_distingue_campos_com_separadores(trecho):
    cap_a = ObraCapitulo(obra_id=1, ordem=1, titulo="A" + trecho, conteudo_md="B")
    cap_b = ObraCapitulo(obra_id=1, ordem=1, titulo="A", conteudo_md=trecho + "B")
    ad_a = Adendo(obra_id=1, codigo="ADO-01", titulo="A" + trecho, texto="B")
    ad_b = Adendo(obra_id=1, codigo="ADO-01", titulo="A", texto=trecho + "B")
    assert hash_capitulo(cap_a) != hash_capitulo(cap_b)
    assert hash_adendo(ad_a) != hash_adendo(ad_b)
    assert hash_canonico({"capitulo:1": hash_capitulo(cap_a)}) != hash_canonico({"capitulo:1": hash_capitulo(cap_b)})


@pytest.mark.parametrize("campo", ["titulo", "conteudo_md"])
@pytest.mark.parametrize("texto,equivalente", [("A\nB\nC", "A\r\nB\rC"),
                                                ("Caf\u00e9", "Cafe\u0301")])
def test_rf03_c10_normalizacao_capitulo(campo, texto, equivalente):
    capitulo = ObraCapitulo(obra_id=1, ordem=1, titulo="Titulo", conteudo_md="Texto")
    setattr(capitulo, campo, texto)
    antes = hash_capitulo(capitulo)
    setattr(capitulo, campo, equivalente)
    assert hash_capitulo(capitulo) == antes


@pytest.mark.parametrize("campo", ["codigo", "titulo", "texto"])
@pytest.mark.parametrize("texto,equivalente", [("A\nB\nC", "A\r\nB\rC"),
                                                ("Caf\u00e9", "Cafe\u0301")])
def test_rf03_c10_normalizacao_adendo(campo, texto, equivalente):
    adendo = Adendo(obra_id=1, codigo="ADO-01", titulo="Nota", texto="Texto")
    setattr(adendo, campo, texto)
    antes = hash_adendo(adendo)
    setattr(adendo, campo, equivalente)
    assert hash_adendo(adendo) == antes


def test_rf03_c10_hash_obra_normaliza_chave_do_adendo(fluxo):
    from sqlmodel import select
    sessao, flow, _, _, _ = fluxo
    obra, _ = preparar(fluxo)
    nota = sessao.exec(select(Adendo).where(Adendo.obra_id == obra.id)).one()
    nota.codigo = "Caf\u00e9"
    sessao.add(nota)
    sessao.flush()
    antes = hash_obra(sessao, obra.id)
    nota.codigo = "Cafe\u0301"
    sessao.add(nota)
    sessao.flush()
    assert hash_obra(sessao, obra.id) == antes


@pytest.mark.parametrize("decisao", ["depende", "nao_entra"])
def test_rf07_c09_liberar_rele_csv_no_mesmo_caminho(fluxo, decisao):
    from gsi_ebd.services import fontes
    sessao, flow, admin, _, inventario = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    assert fontes.fonte_decisao(obra.fonte_id) == "entra"
    inventario.write_text(f"id;decisao\nF-001;{decisao}\n", encoding="utf-8")
    assert fontes.fonte_decisao(obra.fonte_id) == "entra"
    with pytest.raises(FluxoBloqueado, match="fonte"):
        flow.liberar(sessao, versao, "Ajustado", admin)
    assert versao.status == "aguardando_admin"
    assert obra.versao_liberada_id is None


def test_rf07_c09_fonte_regularizada_libera_sem_limpar_cache(fluxo):
    sessao, flow, admin, _, inventario = fluxo
    _, versao = preparar(fluxo, "F-002")
    aprovar(fluxo, versao)
    inventario.write_text("id;decisao\nF-002;entra\n", encoding="utf-8")
    flow.liberar(sessao, versao, "Licenca regularizada", admin)
    assert versao.status == "liberada"


def test_rf08_f10_eventos_append_only_em_todas_as_operacoes(fluxo):
    import json
    from sqlmodel import select
    from gsi_ebd.models import ObraVersaoEvento
    sessao, flow, admin, revisor, _ = fluxo
    anteriores = []

    def executar(tipo, autor, operacao):
        nonlocal anteriores
        versao = operacao()
        sessao.commit()
        sessao.expire_all()
        eventos = sessao.exec(select(ObraVersaoEvento).order_by(ObraVersaoEvento.id)).all()
        registro = [(e.id, e.versao_id, e.tipo, e.autor_id, e.quando, e.detalhe) for e in eventos]
        assert len(registro) == len(anteriores) + 1
        assert registro[:-1] == anteriores
        ultimo = eventos[-1]
        assert ultimo.tipo == tipo and ultimo.autor_id == autor.id
        assert ultimo.versao_id == versao.id and ultimo.quando
        assert json.loads(ultimo.detalhe)["hash"] == versao.conteudo_hash
        anteriores = registro
        return versao, json.loads(ultimo.detalhe)

    obra = Obra(titulo="Trilha")
    versao, _ = executar("importada", admin, lambda: flow.importar(sessao, "F-001", obra, admin))
    for numero in (1, 2):
        parecer = f"Recusa {numero}"
        ajustes = f"Reenvio {numero}"
        _, detalhe = executar("recusada", revisor, lambda: flow.recusar(
            sessao, versao, parecer, revisor, hash_obra(sessao, obra.id)))
        assert detalhe["parecer"] == parecer
        _, detalhe = executar("reenviada", admin, lambda: flow.reenviar(sessao, versao, ajustes, admin))
        assert detalhe["ajustes"] == ajustes
    executar("vista", revisor, lambda: aprovar(fluxo, versao))
    executar("liberada", admin, lambda: flow.liberar(sessao, versao, "Sem ajustes", admin))
    nova, detalhe = executar("alterada", admin, lambda: flow.alterar(sessao, obra, novo_conteudo(), admin))
    assert detalhe["versao_anterior_id"] == versao.id
    executar("vista", revisor, lambda: aprovar(fluxo, nova))
    executar("liberada", admin, lambda: flow.liberar(sessao, nova, "Reavaliada", admin))
    pedido = flow.solicitar_revisao(sessao, nova, revisor, "Reavaliar")
    sessao.commit()
    anteriores = [(e.id, e.versao_id, e.tipo, e.autor_id, e.quando, e.detalhe)
                  for e in sessao.exec(select(ObraVersaoEvento).order_by(ObraVersaoEvento.id)).all()]
    assert pedido.tipo == "revisao_solicitada"
    executar("solicitacao_aceita", admin, lambda: flow.aceitar_solicitacao(sessao, obra, admin))
    assert obra.versao_liberada_id == nova.id and obra.disponibilidade == "suspensa_para_novos"
    assert [json.loads(r[-1])["parecer"] for r in anteriores if r[2] == "recusada"] == ["Recusa 1", "Recusa 2"]


def test_rf08_f10_operacao_bloqueada_nao_acrescenta_evento(fluxo):
    from sqlmodel import select
    from gsi_ebd.models import ObraVersaoEvento
    sessao, flow, admin, _, _ = fluxo
    _, versao = preparar(fluxo)
    antes = sessao.exec(select(ObraVersaoEvento)).all()
    with pytest.raises(FluxoBloqueado):
        flow.liberar(sessao, versao, "Ajustado", admin)
    assert sessao.exec(select(ObraVersaoEvento)).all() == antes


def test_rf08_f10_evento_e_estado_pertencem_a_transacao_do_chamador(fluxo):
    from sqlmodel import select
    from gsi_ebd.models import ObraVersaoEvento
    sessao, flow, _, _, _ = fluxo
    _, versao = preparar(fluxo)
    sessao.commit()
    aprovar(fluxo, versao)
    assert len(sessao.exec(select(ObraVersaoEvento)).all()) == 2
    sessao.rollback()
    assert versao.status == "em_revisao"
    assert [e.tipo for e in sessao.exec(select(ObraVersaoEvento)).all()] == ["importada"]


def test_rf05_delta_alterar_preserva_itens_omitidos_e_hash_completo(fluxo):
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    extra = ObraCapitulo(obra_id=obra.id, ordem=2, titulo="Preservado", conteudo_md="Original 2")
    nota = Adendo(obra_id=obra.id, codigo="ADO-02", texto="Preservada")
    sessao.add_all([extra, nota])
    sessao.flush()
    ids = extra.id, nota.id
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Sem ajustes", admin)
    conteudo = novo_conteudo()
    conteudo["capitulos"].append({"ordem": 3, "titulo": "Adicionado", "conteudo_md": "Novo"})
    nova = flow.alterar(sessao, obra, conteudo, admin)
    sessao.commit()
    sessao.expire_all()
    assert sessao.get(ObraCapitulo, ids[0]).conteudo_md == "Original 2"
    assert sessao.get(Adendo, ids[1]).texto == "Preservada"
    assert len(sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).all()) == 3
    assert len(sessao.exec(select(Adendo).where(Adendo.obra_id == obra.id)).all()) == 2
    assert nova.conteudo_hash == hash_obra(sessao, obra.id)
    assert obra.versao_liberada_id == versao.id



def test_rf07_n01_importar_rele_inventario_com_cache_quente(fluxo):
    from gsi_ebd.services import fontes
    from gsi_ebd.models import ObraVersao, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, _, inventario = fluxo
    assert fontes.fonte_decisao("F-001") == "entra"
    inventario.write_text("id;decisao\nF-001;nao_entra\n", encoding="utf-8")
    assert fontes.fonte_decisao("F-001") == "entra"
    with pytest.raises(FluxoBloqueado, match="fonte"):
        flow.importar(sessao, "F-001", Obra(titulo="Bloqueada"), admin)
    assert sessao.exec(select(Obra)).all() == []
    assert sessao.exec(select(ObraVersao)).all() == []
    assert sessao.exec(select(ObraVersaoEvento)).all() == []


def test_rf05_f06b_liberar_v2_substitui_v1_e_atualiza_catalogo(fluxo):
    sessao, flow, admin, _, _ = fluxo
    obra, primeira = preparar(fluxo)
    aprovar(fluxo, primeira)
    flow.liberar(sessao, primeira, "Inicial", admin)
    original = primeira.hash_liberado
    segunda = flow.alterar(sessao, obra, novo_conteudo(), admin)
    assert primeira.status == "liberada" and obra.status == "em_revisao"
    assert obra.versao_liberada_id == primeira.id
    aprovar(fluxo, segunda)
    flow.liberar(sessao, segunda, "Atualizada", admin)
    sessao.commit()
    sessao.expire_all()
    assert primeira.status == "substituida" and primeira.hash_liberado == original
    assert obra.status == segunda.status == "liberada"
    assert obra.versao_liberada_id == segunda.id


@pytest.mark.parametrize("alterar_texto", [False, True])
def test_rf11_liberar_registra_tamanho_diferenca_no_evento(fluxo, alterar_texto):
    import json
    from gsi_ebd.models import ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    if alterar_texto:
        capitulo = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).one()
        adendo = sessao.exec(select(Adendo).where(Adendo.obra_id == obra.id)).one()
        capitulo.conteudo_md = "Texto ajustado"
        adendo.texto = "Nota ajustada"
        sessao.add_all([capitulo, adendo])
        sessao.flush()
    flow.liberar(sessao, versao, "Ajustes descritos", admin)
    sessao.commit()
    evento = sessao.exec(select(ObraVersaoEvento).where(ObraVersaoEvento.tipo == "liberada")).one()
    assert json.loads(evento.detalhe)["tamanho_diferenca"] == (2 if alterar_texto else 0)


@pytest.mark.parametrize("conteudo", [
    None, [], {}, {"capitulos": []}, {"capitulos": None, "adendos": []},
    {"capitulos": "errado", "adendos": []}, {"capitulos": [None], "adendos": []},
    {"capitulos": [{}], "adendos": []}, {"capitulos": [{"ordem": "errado"}], "adendos": []},
    {"capitulos": [{"ordem": 1, "titulo": None}], "adendos": []},
    {"capitulos": [], "adendos": [{}]}, {"capitulos": [], "adendos": [1]},
    {"capitulos": [], "adendos": [{"codigo": None}]},
])
def test_rf05_alterar_conteudo_malformado_bloqueia_sem_mutacao(fluxo, conteudo):
    from gsi_ebd.models import ObraVersao, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Inicial", admin)
    sessao.commit()
    antes = hash_obra(sessao, obra.id)
    with pytest.raises(FluxoBloqueado, match="malformado"):
        flow.alterar(sessao, obra, conteudo, admin)
    assert hash_obra(sessao, obra.id) == antes
    assert len(sessao.exec(select(ObraVersao)).all()) == 1
    assert len(sessao.exec(select(ObraVersaoEvento)).all()) == 3
    assert obra.versao_liberada_id == versao.id and obra.status == "liberada"


@pytest.mark.parametrize("momento", ["visto", "liberado"])
def test_rf03_snapshot_persiste_texto_normalizado_e_hash_recomputavel(fluxo, momento):
    from gsi_ebd.models import ObraVersaoCapitulo, ObraVersaoAdendo
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    capitulo = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).one()
    adendo = sessao.exec(select(Adendo).where(Adendo.obra_id == obra.id)).one()
    capitulo.titulo = adendo.titulo = "Cafe\u0301\r\nTitulo"
    capitulo.conteudo_md = adendo.texto = "Cafe\u0301\rLinha\r\nFim"
    adendo.codigo = "ADO-Cafe\u0301"
    sessao.add_all([capitulo, adendo])
    sessao.flush()
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Sem ajustes", admin)
    sessao.commit()
    cap = sessao.exec(select(ObraVersaoCapitulo).where(
        ObraVersaoCapitulo.versao_id == versao.id, ObraVersaoCapitulo.momento == momento)).one()
    nota = sessao.exec(select(ObraVersaoAdendo).where(
        ObraVersaoAdendo.versao_id == versao.id, ObraVersaoAdendo.momento == momento)).one()
    assert cap.titulo == nota.titulo == "Caf\u00e9\nTitulo"
    assert cap.conteudo_md == nota.texto == "Caf\u00e9\nLinha\nFim"
    assert nota.codigo == "ADO-Caf\u00e9"
    assert cap.item_hash == hash_capitulo(cap)
    assert nota.item_hash == hash_adendo(nota)
    agregado = hash_canonico({f"capitulo:{cap.ordem}": cap.item_hash,
                             f"adendo:{nota.codigo}": nota.item_hash})
    assert agregado == (versao.hash_visto if momento == "visto" else versao.hash_liberado)


@pytest.mark.parametrize("operacao", ["importar", "liberar"])
def test_rf07_inventario_invalido_capturavel_como_fluxo_bloqueado(fluxo, operacao):
    from gsi_ebd.services.fontes import FonteInvalida
    sessao, flow, admin, _, inventario = fluxo
    _, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    inventario.write_text("id;decisao\nF-001;invalida\n", encoding="utf-8")
    assert issubclass(FonteInvalida, FluxoBloqueado)
    with pytest.raises(FluxoBloqueado):
        if operacao == "importar":
            flow.importar(sessao, "F-001", Obra(titulo="Outra"), admin)
        else:
            flow.liberar(sessao, versao, "Ajustado", admin)



def test_rf11_f11_rodada_apos_recusa_reenvio_preserva_historico(fluxo):
    import json
    from gsi_ebd.models import ObraVersaoCapitulo, ObraVersaoAdendo, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    assert versao.rodada == 0
    aprovar(fluxo, versao)
    sessao.commit()
    assert versao.rodada == 1
    caps = [c.model_dump() for c in sessao.exec(select(ObraVersaoCapitulo)).all()]
    notas = [a.model_dump() for a in sessao.exec(select(ObraVersaoAdendo)).all()]
    eventos = [e.model_dump() for e in sessao.exec(select(ObraVersaoEvento).order_by(ObraVersaoEvento.id)).all()]
    flow.recusar(sessao, versao, "Novo parecer necessario", revisor, hash_obra(sessao, obra.id))
    flow.reenviar(sessao, versao, "Ajustado pelo admin", admin)
    assert versao.rodada == 1
    capitulo = sessao.exec(select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)).one()
    capitulo.conteudo_md = "Visto na rodada 2"
    sessao.add(capitulo)
    sessao.flush()
    aprovar(fluxo, versao)
    assert versao.rodada == 2
    assert flow.diferenca(sessao, versao, atual=True) == []
    capitulo.conteudo_md = "Liberado na rodada 2"
    sessao.add(capitulo)
    flow.liberar(sessao, versao, "Segunda rodada", admin)
    sessao.commit()
    sessao.expire_all()
    diferenca = flow.diferenca(sessao, versao)
    assert len(diferenca) == 1 and diferenca[0]["item"] == "capitulo:1"
    assert diferenca[0]["visto"]["texto"] == "Visto na rodada 2"
    for modelo, antes in ((ObraVersaoCapitulo, caps), (ObraVersaoAdendo, notas)):
        antigos = sessao.exec(select(modelo).where(modelo.rodada == 1)).all()
        assert [item.model_dump() for item in antigos] == antes
    todos = sessao.exec(select(ObraVersaoEvento).order_by(ObraVersaoEvento.id)).all()
    assert [e.model_dump() for e in todos[:len(eventos)]] == eventos
    assert json.loads(todos[-1].detalhe)["tamanho_diferenca"] == 1


def test_rf11_f11_revisao_bloqueada_e_rollback_nao_consumem_rodada(fluxo):
    from gsi_ebd.models import ObraVersaoCapitulo, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.recusar(sessao, versao, "Rever", revisor, hash_obra(sessao, obra.id))
    flow.reenviar(sessao, versao, "Reenviado", admin)
    sessao.commit()
    eventos_antes = len(sessao.exec(select(ObraVersaoEvento)).all())
    with pytest.raises(FluxoBloqueado, match="mudou"):
        flow.revisar(sessao, versao, "Parecer", [], revisor, "hash-desatualizado")
    assert versao.rodada == 1
    aprovar(fluxo, versao)
    assert versao.rodada == 2
    sessao.rollback()
    assert versao.rodada == 1 and versao.status == "em_revisao"
    assert len(sessao.exec(select(ObraVersaoEvento)).all()) == eventos_antes
    assert not sessao.exec(select(ObraVersaoCapitulo).where(ObraVersaoCapitulo.rodada == 2)).all()


def test_rf11_f11_diferenca_nao_inclui_itens_de_rodadas_antigas(fluxo):
    from gsi_ebd.models import ObraVersaoCapitulo, ObraVersaoAdendo
    sessao, flow, _, _, _ = fluxo
    _, versao = preparar(fluxo)
    versao.rodada = 2
    sessao.add(versao)
    # A ordem fisica dos registros nao identifica a rodada corrente.
    for rodada in (2, 1):
        for momento in ("visto", "liberado"):
            cap = ObraVersaoCapitulo(
                versao_id=versao.id, rodada=rodada, momento=momento, ordem=1,
                titulo="Titulo", conteudo_md=f"Capitulo {momento} da rodada {rodada}")
            nota = ObraVersaoAdendo(
                versao_id=versao.id, rodada=rodada, momento=momento, codigo="ADO-01",
                titulo="Nota", texto=f"Adendo {momento} da rodada {rodada}")
            cap.item_hash = hash_capitulo(cap)
            nota.item_hash = hash_adendo(nota)
            sessao.add_all([cap, nota])
    # Itens exclusivamente historicos nao pertencem a rodada corrente.
    for momento in ("visto", "liberado"):
        cap = ObraVersaoCapitulo(
            versao_id=versao.id, rodada=1, momento=momento, ordem=99,
            titulo="Historico", conteudo_md=f"Antigo {momento}")
        nota = ObraVersaoAdendo(
            versao_id=versao.id, rodada=1, momento=momento, codigo="ADO-99",
            titulo="Historica", texto=f"Antiga {momento}")
        cap.item_hash = hash_capitulo(cap)
        nota.item_hash = hash_adendo(nota)
        sessao.add_all([cap, nota])
    sessao.commit()
    mudancas = {item["item"]: item for item in flow.diferenca(sessao, versao)}
    assert set(mudancas) == {"capitulo:1", "adendo:ADO-01"}
    assert mudancas["capitulo:1"]["visto"]["texto"] == "Capitulo visto da rodada 2"
    assert mudancas["capitulo:1"]["liberado"]["texto"] == "Capitulo liberado da rodada 2"
    assert mudancas["adendo:ADO-01"]["visto"]["texto"] == "Adendo visto da rodada 2"
    assert mudancas["adendo:ADO-01"]["liberado"]["texto"] == "Adendo liberado da rodada 2"



def obra_publicada(fluxo):
    sessao, flow, admin, _, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Publicacao inicial", admin)
    sessao.commit()
    return obra, versao


@pytest.mark.parametrize("abertura", ["alterar", "aceitar"])
@pytest.mark.parametrize("fechamento", ["liberar", "cancelar"])
def test_rf12_f12_disponibilidade_so_muda_pelo_admin(fluxo, abertura, fechamento):
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    flow.solicitar_revisao(sessao, original, revisor, "Revisar a obra")
    assert obra.disponibilidade == "aberta" and obra.versao_liberada_id == original.id
    if abertura == "alterar":
        nova = flow.alterar(sessao, obra, novo_conteudo(), admin)
    else:
        nova = flow.aceitar_solicitacao(sessao, obra, admin)
    assert obra.disponibilidade == "suspensa_para_novos"
    assert obra.versao_liberada_id == original.id and original.status == "liberada"
    aprovar(fluxo, nova)
    assert obra.disponibilidade == "suspensa_para_novos"
    assert obra.versao_liberada_id == original.id
    if fechamento == "liberar":
        flow.liberar(sessao, nova, "Ajustes concluidos", admin)
        assert obra.versao_liberada_id == nova.id and original.status == "substituida"
    else:
        flow.cancelar_ciclo(sessao, obra, admin)
        assert obra.versao_liberada_id == original.id and original.status == "liberada"
    sessao.commit()
    sessao.expire_all()
    assert obra.disponibilidade == "aberta"


def test_rf13_f13_solicitacao_dispensa_com_motivo_visivel_e_novo_pedido(fluxo):
    import json
    from gsi_ebd.models import ObraVersao, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    pedido = flow.solicitar_revisao(sessao, original, revisor, "Checar notas")
    sessao.commit()
    sessao.refresh(original)
    estado = original.model_dump()
    for motivo in ("", "  ", None):
        with pytest.raises(FluxoBloqueado, match="Motivo"):
            flow.dispensar_solicitacao(sessao, obra, admin, motivo)
    resposta = flow.dispensar_solicitacao(sessao, obra, admin, "Ja verificado na revisao anterior")
    sessao.commit()
    sessao.refresh(original)
    assert original.model_dump() == estado
    assert obra.disponibilidade == "aberta" and obra.versao_liberada_id == original.id
    assert len(sessao.exec(select(ObraVersao)).all()) == 1
    detalhe = json.loads(resposta.detalhe)
    assert detalhe["solicitacao_id"] == pedido.id
    assert detalhe["motivo"] == "Ja verificado na revisao anterior"
    assert sessao.get(ObraVersaoEvento, resposta.id).autor_id == admin.id
    with pytest.raises(FluxoBloqueado, match="Nenhuma"):
        flow.aceitar_solicitacao(sessao, obra, admin)
    novo_pedido = flow.solicitar_revisao(sessao, original, revisor, "Nova evidencia")
    nova = flow.aceitar_solicitacao(sessao, obra, admin)
    assert nova.numero == 2 and nova.id != original.id
    evento = sessao.exec(select(ObraVersaoEvento).where(
        ObraVersaoEvento.tipo == "solicitacao_aceita")).one()
    assert json.loads(evento.detalhe)["solicitacao_id"] == novo_pedido.id


@pytest.mark.parametrize("operacao", ["aceitar", "dispensar", "cancelar"])
@pytest.mark.parametrize("papel", [p for p in Role if p != Role.ADMIN])
def test_rf13_f13_f15_decisoes_de_ciclo_exigem_admin(fluxo, operacao, papel):
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    flow.solicitar_revisao(sessao, original, revisor, "Rever")
    if operacao == "cancelar":
        flow.aceitar_solicitacao(sessao, obra, admin)
    usuario = User(id=123, email="outro@example.test", role=papel)
    with pytest.raises(FluxoBloqueado, match="Papel"):
        if operacao == "aceitar":
            flow.aceitar_solicitacao(sessao, obra, usuario)
        elif operacao == "dispensar":
            flow.dispensar_solicitacao(sessao, obra, usuario, "Nao procede")
        else:
            flow.cancelar_ciclo(sessao, obra, usuario)
    assert obra.versao_liberada_id == original.id


def test_rf13_f13_nao_aceita_pedido_duplicado_ou_ciclo_paralelo(fluxo):
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    flow.solicitar_revisao(sessao, original, revisor, "Rever")
    with pytest.raises(FluxoBloqueado):
        flow.solicitar_revisao(sessao, original, revisor, "Duplicado")
    flow.alterar(sessao, obra, novo_conteudo(), admin)
    with pytest.raises(FluxoBloqueado, match="ciclo pendente"):
        flow.aceitar_solicitacao(sessao, obra, admin)


def test_rf14_f14_vinculo_fixa_versao_e_suspensao_bloqueia_so_novos(fluxo):
    from gsi_ebd.models import Ambiente, VinculoObra, ObraVersaoCapitulo
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, original = obra_publicada(fluxo)
    coordenador = User(email="coord@example.test", role=Role.COORDENADOR)
    sessao.add(coordenador)
    sessao.flush()
    ambiente = Ambiente(nome="Ambiente", coordenador_id=coordenador.id)
    sessao.add(ambiente)
    sessao.flush()
    vinculo = flow.vincular(sessao, ambiente, obra, coordenador)
    assert vinculo.versao_id == original.id
    nova = flow.alterar(sessao, obra, novo_conteudo(), admin)
    with pytest.raises(FluxoBloqueado, match="indisponivel"):
        flow.vincular(sessao, ambiente, obra, coordenador)
    assert vinculo.ativo and vinculo.versao_id == original.id
    aprovar(fluxo, nova)
    flow.liberar(sessao, nova, "Concluido", admin)
    novo_vinculo = flow.vincular(sessao, ambiente, obra, coordenador)
    sessao.commit()
    sessao.expire_all()
    assert sessao.get(VinculoObra, vinculo.id).versao_id == original.id
    assert novo_vinculo.versao_id == nova.id
    assert original.status == "substituida"
    publicado = sessao.exec(select(ObraVersaoCapitulo).where(
        ObraVersaoCapitulo.versao_id == vinculo.versao_id,
        ObraVersaoCapitulo.momento == "liberado")).one()
    assert publicado.conteudo_md == "Original"
    outro = User(email="outro-coord@example.test", role=Role.COORDENADOR)
    sessao.add(outro)
    sessao.flush()
    with pytest.raises(FluxoBloqueado, match="escopo"):
        flow.vincular(sessao, ambiente, obra, outro)


def test_rf15_f15_cancelar_preserva_evidencias_reabre_e_impede_liberar_descartada(fluxo):
    from gsi_ebd.models import ObraVersaoEvento, ObraVersaoCapitulo
    from sqlmodel import select
    sessao, flow, admin, _, _ = fluxo
    obra, original = obra_publicada(fluxo)
    nova = flow.alterar(sessao, obra, novo_conteudo(), admin)
    aprovar(fluxo, nova)
    antes = len(sessao.exec(select(ObraVersaoCapitulo)).all())
    flow.cancelar_ciclo(sessao, obra, admin)
    sessao.commit()
    assert nova.status == "cancelada" and obra.disponibilidade == "aberta"
    assert obra.versao_liberada_id == original.id and original.status == "liberada"
    assert len(sessao.exec(select(ObraVersaoCapitulo)).all()) == antes
    assert sessao.exec(select(ObraVersaoEvento).where(ObraVersaoEvento.tipo == "ciclo_cancelado")).one()
    with pytest.raises(FluxoBloqueado):
        flow.liberar(sessao, nova, "Nao pode", admin)
    with pytest.raises(FluxoBloqueado):
        flow.cancelar_ciclo(sessao, obra, admin)
    proxima = flow.alterar(sessao, obra, novo_conteudo(), admin)
    assert proxima.id != nova.id and proxima.numero > nova.numero


@pytest.mark.parametrize("posicao", ["concordo", "objeto"])
def test_rf16_f16_posicao_nao_bloqueia_decisao_do_admin(fluxo, posicao):
    import json
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    flow.solicitar_revisao(sessao, original, revisor, "Reavaliar")
    nova = flow.aceitar_solicitacao(sessao, obra, admin)
    antes = obra.versao_liberada_id, obra.disponibilidade, nova.status
    evento = flow.posicionar(sessao, nova, revisor, posicao, "Posicao registrada")
    assert evento.tipo == "posicao" and evento.autor_id == revisor.id
    assert json.loads(evento.detalhe)["posicao"] == posicao
    assert (obra.versao_liberada_id, obra.disponibilidade, nova.status) == antes
    aprovar(fluxo, nova)
    flow.liberar(sessao, nova, "Concluido pelo admin", admin)
    assert nova.status == "liberada" and obra.disponibilidade == "aberta"


@pytest.mark.parametrize("operacao", ["solicitar", "posicionar"])
@pytest.mark.parametrize("papel", [p for p in Role if p != Role.REVISOR])
def test_rf13_f13_f16_pedidos_e_posicoes_exigem_revisor(fluxo, operacao, papel):
    sessao, flow, _, _, _ = fluxo
    _, versao = obra_publicada(fluxo)
    usuario = User(id=123, email="outro@example.test", role=papel)
    with pytest.raises(FluxoBloqueado, match="Papel"):
        if operacao == "solicitar":
            flow.solicitar_revisao(sessao, versao, usuario, "Reavaliar")
        else:
            flow.posicionar(sessao, versao, usuario, "objeto", "Texto")


def test_rf13_f13_decisoes_e_pedidos_compartilham_transacao(fluxo):
    from gsi_ebd.models import ObraVersao, ObraVersaoEvento
    from sqlmodel import select
    sessao, flow, admin, revisor, _ = fluxo
    obra, original = obra_publicada(fluxo)
    pedido = flow.solicitar_revisao(sessao, original, revisor, "Rever")
    sessao.commit()
    flow.aceitar_solicitacao(sessao, obra, admin)
    sessao.rollback()
    assert obra.disponibilidade == "aberta" and obra.versao_liberada_id == original.id
    assert len(sessao.exec(select(ObraVersao)).all()) == 1
    assert not sessao.exec(select(ObraVersaoEvento).where(ObraVersaoEvento.tipo == "solicitacao_aceita")).all()
    resposta = flow.dispensar_solicitacao(sessao, obra, admin, "Dispensa apos rollback")
    assert resposta.versao_id == pedido.versao_id
