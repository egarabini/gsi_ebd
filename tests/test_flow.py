"""DEM-011: C-02/C-03 e primitivas de permissao RF02."""
from hashlib import sha256

import pytest
from sqlmodel import Session, SQLModel, create_engine

from gsi_ebd.models import Adendo, Obra, ObraCapitulo, Role, User
from gsi_ebd.services.flow import (
    FluxoBloqueado, exigir_papel, hash_adendo, hash_capitulo,
    hash_canonico, hash_obra, tamanho_diferenca,
)


def test_rf03_c02_vetor_canonico_v2():
    capitulo = ObraCapitulo(obra_id=1, ordem=2, titulo="Titulo", conteudo_md="Linha\nTexto")
    adendo = Adendo(obra_id=1, codigo="ADO-01", titulo="Nota", texto="Texto")
    cap_hash = sha256(b"2|Titulo|Linha\nTexto").hexdigest()
    ad_hash = sha256(b"ADO-01|Nota|Texto").hexdigest()
    esperado = sha256(("v1|" + "|".join(sorted([cap_hash, ad_hash]))).encode()).hexdigest()
    assert hash_capitulo(capitulo) == cap_hash
    assert hash_adendo(adendo) == ad_hash
    assert hash_canonico([cap_hash, ad_hash]) == esperado
    assert hash_canonico([ad_hash, cap_hash]) == esperado
    assert hash_canonico([]) == sha256(b"v1|").hexdigest()


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
            esperado = hash_canonico([hash_capitulo(capitulo), hash_adendo(adendo)])
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
    assert versao.status == obra.status == "liberada"
    assert nova.numero == 2 and nova.status == "em_revisao"
    assert nova.conteudo_hash == flow.hash_obra(sessao, obra.id) != original


def test_rf11_f06_contestar_preserva_assinaturas(fluxo):
    sessao, flow, admin, revisor, _ = fluxo
    obra, versao = preparar(fluxo)
    aprovar(fluxo, versao)
    flow.liberar(sessao, versao, "Ajustado", admin)
    antes = versao.hash_liberado
    nova = flow.contestar(sessao, versao, revisor)
    assert nova.id != versao.id and nova.numero == 2 and nova.status == "em_revisao"
    assert versao.status == "liberada" and versao.hash_liberado == antes
    assert obra.versao_liberada_id == versao.id


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
