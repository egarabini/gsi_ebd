"""Testes do importador do estudo aplicavel — as partes puras.

O caminho de banco (carga, idempotencia, pre-condicao da obra) e provado pelo
`--autoteste` do proprio importador, que roda 10 verificacoes em SQLite descartavel.
"""
from datetime import datetime
from types import SimpleNamespace

from gsi_ebd.scripts.importar_estudo_aplicado import (
    escolher_versao,
    ordem_do_titulo,
    selecionar_estudos,
)


def _versao(numero, criada=None):
    return SimpleNamespace(version=numero, created_at=criada)


def test_ordem_do_titulo_le_o_padrao_real():
    # Os 34 capitulos do Grudem em producao seguem exatamente este padrao.
    assert ordem_do_titulo("Cap. 01 — Introdução à Teologia Sistemática") == 1
    assert ordem_do_titulo("Cap. 21 — Conversão (Fé e Arrependimento)") == 21
    assert ordem_do_titulo("Cap. 34 — Novos Céus e Nova Terra") == 34
    assert ordem_do_titulo("Cap.29 — Dons") == 29


def test_ordem_do_titulo_ignora_os_estudos_de_exemplo():
    # Os 5 estudos de exemplo NAO seguem o padrao e ficam de fora (decisao 8.2).
    assert ordem_do_titulo("O Plano da Salvação") is None
    assert ordem_do_titulo("Hermenêutica Bíblica") is None
    assert ordem_do_titulo("Capítulo 7") is None
    assert ordem_do_titulo("") is None
    assert ordem_do_titulo(None) is None


def test_escolher_versao_pega_a_de_maior_numero():
    assert escolher_versao([_versao(1), _versao(3), _versao(2)]).version == 3


def test_escolher_versao_desempata_pela_mais_recente():
    antiga = _versao(2, datetime(2026, 1, 1))
    recente = _versao(2, datetime(2026, 6, 1))
    assert escolher_versao([antiga, recente]) is recente


def test_escolher_versao_sem_versao_devolve_none():
    assert escolher_versao([]) is None
    assert escolher_versao([None]) is None


def test_selecionar_estudos_separa_e_ordena_pela_ordem():
    estudos = [
        SimpleNamespace(id=1, title="Exemplo 1"),
        SimpleNamespace(id=6, title="Cap. 01 — Um"),
        SimpleNamespace(id=2, title="Exemplo 2"),
        SimpleNamespace(id=9, title="Cap. 04 — Quatro"),
    ]
    selecionados, ignorados = selecionar_estudos(estudos)

    assert [ordem for ordem, _ in selecionados] == [1, 4]
    assert [estudo.id for _, estudo in selecionados] == [6, 9]
    assert [estudo.id for estudo in ignorados] == [1, 2]
