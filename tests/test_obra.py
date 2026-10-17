"""Testes do importador de OBRA — as partes puras.

A leitura de arquivos em si é provada pelo `--autoteste` do importador, que roda
sobre os 34 capítulos reais do DOUTRINAS_CRISTAS e confere títulos e ordem.
"""
from gsi_ebd.scripts.importar_obra import (
    DOUTRINAS_INICIAIS,
    SUFIXOS,
    ler_titulo,
    ordem_da_pasta,
)


def test_ordem_da_pasta():
    from pathlib import Path

    assert ordem_da_pasta(Path("Capitulo_01")) == 1
    assert ordem_da_pasta(Path("Capitulo_34")) == 34
    assert ordem_da_pasta(Path("Capitulo_9")) == 9
    assert ordem_da_pasta(Path("outra_pasta")) is None
    assert ordem_da_pasta(Path("Capitulo_")) is None


def test_ler_titulo_pega_o_primeiro_h1():
    assert ler_titulo("# Introdução à Teologia\n\n## Perguntas") == "Introdução à Teologia"
    assert ler_titulo("> citação\n# Conversão\n") == "Conversão"
    assert ler_titulo("#   Espaços   ") == "Espaços"


def test_ler_titulo_sem_h1_devolve_vazio():
    assert ler_titulo("") == ""
    assert ler_titulo(None) == ""
    assert ler_titulo("## Só h2\n\ntexto") == ""
    assert ler_titulo("texto sem título") == ""


def test_a_versao_corrigida_e_preferida_a_preservada():
    """A convenção do projeto: `_PT_v1` é a corrigida, `_PT` é a preservada.

    Conferir a ORDEM da tupla é o que garante que o importador pega a boa quando
    as duas existirem — e o autoteste cobre o caso real (hoje só há `_PT`).
    """
    assert SUFIXOS[0] == "_PT_v1.md"
    assert SUFIXOS[1] == "_PT.md"


def test_doutrinas_iniciais_sao_orientacao_e_nao_portao():
    """A lista é cadastrável e serve de orientação — não de bloqueio."""
    assert "Batista" in DOUTRINAS_INICIAIS
    assert "Pentecostal" in DOUTRINAS_INICIAIS
    assert "Presbiteriano" in DOUTRINAS_INICIAIS
    assert "Adventista" in DOUTRINAS_INICIAIS
    assert len(DOUTRINAS_INICIAIS) >= 4
