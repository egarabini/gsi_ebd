"""Testes da curadoria de passagens relacionadas (referências cruzadas do OpenBible).

O que estes testes protegem (ver Diagnostico/referencias-cruzadas.md):
- o piso de votos, porque os votos são um SALDO e podem ser negativos — sem piso
  uma relação rejeitada pela comunidade entraria na lição;
- o teto de 5 por lição, porque no corte de votos ≥ 10 a média era de 21,7
  passagens por citação;
- o rodízio entre as citações, para o bloco não ficar dominado por uma só;
- a atribuição CC-BY, que é obrigação da licença.

Nada aqui toca no banco nem no corpus: `selecionar` e `renderizar` são puras.
"""
from gsi_ebd.services.referencias_cruzadas_service import (
    ATRIBUICAO,
    MAX_RELACIONADAS,
    VOTOS_MINIMOS,
    PassagemRelacionada,
    ReferenciasCruzadasService,
    chave_osis,
    parse_destino,
    renderizar,
    selecionar,
)
from gsi_ebd.services.escritura_service import EscrituraService
from gsi_ebd.utils.livros import por_osis


def passagem(osis_livro: str, cap: int, ver: int, votos: int, origem: str, fim: int = 0):
    return PassagemRelacionada(
        livro=por_osis(osis_livro),
        capitulo=cap,
        versiculo=ver,
        versiculo_fim=fim or ver,
        votos=votos,
        origem=origem,
    )


# ── conversão de chaves ─────────────────────────────────────────────────────

def test_chave_osis_usa_o_codigo_do_dataset():
    """A chave do lado 'de' é OSIS com pontos — e é o que o mapa já guarda."""
    citacao = EscrituraService.extrair_citacoes("Jo 3.16")[0]
    assert chave_osis(citacao) == "John.3.16"
    citacao = EscrituraService.extrair_citacoes("Jó 1.21")[0]
    assert chave_osis(citacao) == "Job.1.21"


def test_parse_destino_simples():
    p = parse_destino("Ps.115.15", origem="Gen.1.1", votos=83)
    assert p is not None
    assert p.rotulo == "Salmos 115:15"
    assert p.votos == 83
    assert p.versiculo_fim == p.versiculo


def test_parse_destino_intervalo():
    """25,6% dos pares do arquivo são intervalo, sempre repetindo livro e capítulo."""
    p = parse_destino("Rom.8.5-Rom.8.8", origem="1Cor.2.14", votos=57)
    assert p is not None
    assert p.rotulo == "Romanos 8:5-8"
    assert (p.capitulo, p.versiculo, p.versiculo_fim) == (8, 5, 8)


def test_parse_destino_intervalo_com_livro_diferente_nao_inventa():
    """Forma que não existe no arquivo: fica só o primeiro versículo, que é o seguro."""
    p = parse_destino("Rom.8.5-John.3.16", origem="x", votos=5)
    assert p is not None
    assert p.rotulo == "Romanos 8:5"


def test_parse_destino_recusa_o_que_nao_conhece():
    for lixo in ("", "NaoExiste.1.1", "Gen", "Gen.1", "1.2.3", None):
        assert parse_destino(lixo, origem="x", votos=1) is None


def test_parse_destino_livros_numerados():
    assert parse_destino("1Cor.13.4", "x", 5).rotulo == "1 Coríntios 13:4"
    assert parse_destino("2John.1.6", "x", 5).rotulo == "2 João 1:6"
    assert parse_destino("1Thess.5.17", "x", 5).rotulo == "1 Tessalonicenses 5:17"


# ── curadoria ───────────────────────────────────────────────────────────────

def test_teto_de_cinco_por_licao():
    """9 candidatos distintos, 3 origens: o bloco para em 5."""
    candidatos = [
        passagem("Rom", 5, i * 10 + v, 100 - v, origem=f"origem{i}")
        for i in range(3)
        for v in (1, 2, 3)
    ]
    escolhidas = selecionar(candidatos)
    assert len(escolhidas) == MAX_RELACIONADAS == 5
    assert len({p.chave for p in escolhidas}) == 5  # sem repetição


def test_rodizio_entre_as_citacoes():
    """Cada origem contribui com a sua melhor antes de qualquer uma dar a segunda."""
    candidatos = [
        passagem("Rom", 5, 8, 100, origem="Joao.3.16"),
        passagem("Rom", 5, 9, 90, origem="Joao.3.16"),
        passagem("Eph", 2, 8, 95, origem="Rom.3.23"),
        passagem("Isa", 53, 6, 50, origem="Heb.9.22"),
    ]
    escolhidas = selecionar(candidatos, maximo=5)
    assert [p.origem for p in escolhidas] == ["Joao.3.16", "Rom.3.23", "Heb.9.22", "Joao.3.16"]


def test_ordena_por_votos_dentro_da_origem():
    candidatos = [
        passagem("Rom", 5, 1, 30, origem="A"),
        passagem("Rom", 5, 2, 90, origem="A"),
        passagem("Rom", 5, 3, 60, origem="A"),
    ]
    assert [p.votos for p in selecionar(candidatos)] == [90, 60, 30]


def test_nao_repete_a_mesma_passagem():
    candidatos = [
        passagem("Rom", 5, 8, 100, origem="A"),
        passagem("Rom", 5, 8, 99, origem="B"),
        passagem("Rom", 5, 8, 98, origem="C"),
    ]
    assert len(selecionar(candidatos)) == 1


def test_nao_sugere_o_que_o_plano_ja_cita():
    citada = ("Rom", 3, 23, 23)
    candidatos = [
        passagem("Rom", 3, 23, 999, origem="A"),
        passagem("Rom", 3, 24, 50, origem="A"),
    ]
    escolhidas = selecionar(candidatos, ja_citadas={citada})
    assert [p.rotulo for p in escolhidas] == ["Romanos 3:24"]


def test_sem_candidatos_devolve_vazio():
    assert selecionar([]) == []


# ── renderização ────────────────────────────────────────────────────────────

def test_sem_passagens_nao_renderiza_nada():
    assert renderizar([], lambda p: "texto") == ""


def test_renderiza_com_atribuicao_obrigatoria():
    """CC-BY exige atribuição: ela tem de estar no texto renderizado."""
    escolhidas = [passagem("Rom", 5, 8, 100, origem="A")]
    bloco = renderizar(escolhidas, lambda p: "Mas Deus prova o seu amor")
    assert ATRIBUICAO in bloco
    assert "OpenBible.info" in bloco
    assert "**Romanos 5:8** — Mas Deus prova o seu amor" in bloco


def test_renderiza_mesmo_sem_texto_do_corpus():
    """Sem o corpus, a referência ainda aparece — só sem o texto."""
    escolhidas = [passagem("Rom", 5, 8, 100, origem="A")]
    bloco = renderizar(escolhidas, lambda p: "")
    assert "**Romanos 5:8**" in bloco
    assert " — " not in bloco


def test_renderiza_uma_linha_por_passagem():
    escolhidas = [
        passagem("Rom", 5, 8, 100, origem="A"),
        passagem("Eph", 2, 8, 90, origem="A"),
    ]
    bloco = renderizar(escolhidas, lambda p: "x")
    assert bloco.count(" — x") == 2  # uma linha de texto por passagem
    assert bloco.startswith("> *")   # a atribuição abre o bloco


# ── degradação ──────────────────────────────────────────────────────────────

def test_bloco_sem_citacoes_no_plano_devolve_vazio():
    assert ReferenciasCruzadasService.bloco("") == ""
    assert ReferenciasCruzadasService.bloco("texto sem referencia biblica alguma") == ""


def test_bloco_degrada_em_silencio_sem_banco():
    """Sem banco configurado, o bloco some — a lição não pode quebrar por isso."""
    assert ReferenciasCruzadasService.bloco("Passagens: Rm 3.23 e Jo 3.16") == ""


def test_piso_de_votos_e_positivo():
    """Os votos podem ser negativos (mínimo −86 no arquivo): o piso é proteção."""
    assert VOTOS_MINIMOS > 0
