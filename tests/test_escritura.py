"""Testes do EscrituraService: extração de citações e busca exata por referência.

Contexto (Diagnostico/referencias-cruzadas.md): a busca por referência usava
similaridade semântica, com a referência como consulta. Medido em produção:
`buscar('João 3:16')` devolvia Mateus 4:12 (0.647) e João 4:1 (0.630) — os dois
acima do corte de 0.55, prontos para aparecer na lição como se fossem a citação.

Referência se acha por IGUALDADE. Estes testes travam isso.
"""
from gsi_ebd.services.escritura_service import Citacao, EscrituraService
from gsi_ebd.utils.livros import por_osis, resolver


class ColecaoFalsa:
    """Substitui a coleção do ChromaDB: registra os `where` e devolve do dicionário."""

    def __init__(self, dados: dict):
        self.dados = dados
        self.consultas: list = []

    def get(self, where=None):  # noqa: A003 - mesma assinatura da coleção real
        chave = (where or {}).get("referencia")
        self.consultas.append(chave)
        if chave in self.dados:
            return {
                "documents": [self.dados[chave]],
                "metadatas": [{"referencia": chave}],
            }
        return {"documents": [], "metadatas": []}


def servico_com(dados: dict) -> tuple:
    srv = EscrituraService()
    fake = ColecaoFalsa(dados)
    srv._colecao = fake  # _conectar() devolve o que já estiver aqui
    return srv, fake


# ── extração: o bug do Jo/Jó mora aqui ──────────────────────────────────────

def test_extrair_citacoes_resolve_jo_como_joao():
    (citacao,) = EscrituraService.extrair_citacoes("**Jo 3.16** — o amor de Deus")
    assert citacao.livro.osis == "John"
    assert (citacao.capitulo, citacao.versiculo) == (3, 16)
    assert citacao.texto == "João 3:16"


def test_extrair_citacoes_resolve_jo_acentuado_como_o_livro_de_jo():
    (citacao,) = EscrituraService.extrair_citacoes("Jó 1.21")
    assert citacao.livro.osis == "Job"
    assert citacao.texto == "Jó 1:21"


def test_extrair_citacoes_intervalo():
    (citacao,) = EscrituraService.extrair_citacoes("Mt 28.19-20")
    assert (citacao.versiculo, citacao.versiculo_fim) == (19, 20)
    assert citacao.texto == "Mateus 28:19-20"


def test_extrair_citacoes_acento_e_espaco():
    textos = [c.texto for c in EscrituraService.extrair_citacoes("Êx 34.6-7 e 1 Co 13.4")]
    assert textos == ["Êxodo 34:6-7", "1 Coríntios 13:4"]


def test_extrair_referencias_continua_devolvendo_texto():
    """Contrato antigo, usado pelo review_service: lista de strings."""
    assert EscrituraService.extrair_referencias("Rm 3.23") == ["Romanos 3:23"]
    assert EscrituraService.extrair_referencias("") == []
    assert EscrituraService.extrair_referencias(None) == []


# ── a chave exata do índice ─────────────────────────────────────────────────

def test_chave_do_corpus_para_joao_e_jo():
    """O corpus grava sem acento: João -> 'Joao', Jó -> 'Jo'."""
    assert por_osis("John").referencia_corpus(3, 16) == "Joao 3:16"
    assert por_osis("Job").referencia_corpus(1, 21) == "Jo 1:21"
    assert por_osis("Gen").referencia_corpus(1, 1) == "Genesis 1:1"


def test_chave_do_corpus_para_as_tres_grafias_proprias():
    """Medido contra PREFIXO_LIVRO: só estes três não saem da normalização."""
    assert por_osis("Song").nome_corpus == "Cantares"
    assert por_osis("Obad").nome_corpus == "Abdias"
    assert por_osis("Phlm").nome_corpus == "Filemon"


def test_nome_corpus_de_todos_os_livros_e_sem_acento_e_sem_espaco():
    from gsi_ebd.utils.livros import LIVROS

    for livro in LIVROS:
        assert livro.nome_corpus, livro.nome
        assert " " not in livro.nome_corpus, livro.nome
        assert livro.nome_corpus.isascii(), livro.nome


def test_chaves_do_corpus_expandem_intervalo():
    citacao = Citacao(livro=por_osis("Matt"), capitulo=28, versiculo=19, versiculo_fim=20)
    assert citacao.chaves_corpus() == ["Mateus 28:19", "Mateus 28:20"]


def test_chaves_do_corpus_cortam_intervalo_longo():
    citacao = Citacao(livro=por_osis("Ps"), capitulo=119, versiculo=1, versiculo_fim=176)
    assert len(citacao.chaves_corpus(maximo=5)) == 5
    assert citacao.chaves_corpus(maximo=5)[0] == "Salmos 119:1"


# ── a busca exata (o ponto do conserto) ─────────────────────────────────────

def test_buscar_citacao_usa_igualdade_e_acha_o_versiculo_certo():
    srv, fake = servico_com({"Joao 3:16": "Porque Deus amou o mundo de tal maneira"})
    citacao = EscrituraService.extrair_citacoes("Jo 3.16")[0]
    achados = srv.buscar_citacao(citacao)
    assert fake.consultas == ["Joao 3:16"]  # consultou a chave exata
    assert len(achados) == 1
    assert achados[0].referencia == "Joao 3:16"
    assert achados[0].texto.startswith("Porque Deus amou")
    assert achados[0].score == 1.0


def test_buscar_citacao_nao_devolve_versiculo_errado_quando_nao_acha():
    """O comportamento antigo devolvia Mateus 4:12; o novo devolve nada."""
    srv, fake = servico_com({})  # coleção vazia
    citacao = EscrituraService.extrair_citacoes("Jo 3.16")[0]
    assert srv.buscar_citacao(citacao) == []
    assert fake.consultas == ["Joao 3:16"]


def test_buscar_citacao_de_intervalo_junta_os_versiculos():
    srv, _ = servico_com({
        "Mateus 28:19": "Portanto ide, ensinai todas as nações",
        "Mateus 28:20": "Ensinando-os a guardar todas as coisas",
    })
    citacao = EscrituraService.extrair_citacoes("Mt 28.19-20")[0]
    achados = srv.buscar_citacao(citacao)
    assert [v.referencia for v in achados] == ["Mateus 28:19", "Mateus 28:20"]


def test_buscar_referencias_remove_repeticao():
    srv, _ = servico_com({"Joao 3:16": "Porque Deus amou o mundo"})
    citacoes = EscrituraService.extrair_citacoes("Jo 3.16 ... de novo Jo 3.16")
    assert len(citacoes) == 1  # a extração já deduplica
    assert len(srv.buscar_referencias(citacoes)) == 1


def test_buscar_referencias_sem_colecao_nao_quebra():
    srv = EscrituraService()
    srv._indisponivel = True
    citacoes = EscrituraService.extrair_citacoes("Jo 3.16")
    assert srv.buscar_referencias(citacoes) == []


def test_resolver_continua_recusando_lixo():
    assert resolver("capitulo") is None
    assert EscrituraService.extrair_citacoes("capitulo 3.1 nao e referencia") == []
