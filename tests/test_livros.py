"""Testes do mapa canônico de livros e da extração de referências.

Contexto (ver Diagnostico/referencias-cruzadas.md): o mapa antigo do
`escritura_service` resolvia `"jo"` como **Jó**, o livro, enquanto a convenção de
abreviaturas dos estudos (AGENTS.md do DOUTRINAS_CRISTAS) usa **Jo = João**.
Como `Jó 3:16` existe, a lição exibia o versículo errado sem erro nenhum.

Medido nos 34 planos: 17 citações apontando para o livro errado e 2 descartadas
por causa do acento (`Êx`). Estes testes travam a correção.
"""
from gsi_ebd.services.escritura_service import EscrituraService
from gsi_ebd.utils.livros import LIVROS, por_ordem, por_osis, resolver, sem_acento

# Exatamente os 66 códigos de livro presentes em cross_references.txt (OpenBible).
# O mapa precisa bater com o DADO, não com a memória de quem escreveu o mapa.
OSIS_DO_DATASET = {
    "1Chr", "1Cor", "1John", "1Kgs", "1Pet", "1Sam", "1Thess", "1Tim",
    "2Chr", "2Cor", "2John", "2Kgs", "2Pet", "2Sam", "2Thess", "2Tim",
    "3John", "Acts", "Amos", "Col", "Dan", "Deut", "Eccl", "Eph", "Esth",
    "Exod", "Ezek", "Ezra", "Gal", "Gen", "Hab", "Hag", "Heb", "Hos", "Isa",
    "Jas", "Jer", "Job", "Joel", "John", "Jonah", "Josh", "Jude", "Judg",
    "Lam", "Lev", "Luke", "Mal", "Mark", "Matt", "Mic", "Nah", "Neh", "Num",
    "Obad", "Phil", "Phlm", "Prov", "Ps", "Rev", "Rom", "Ruth", "Song",
    "Titus", "Zech", "Zeph",
}


# ── integridade da tabela ───────────────────────────────────────────────────

def test_sao_66_livros_em_ordem_continua():
    assert len(LIVROS) == 66
    assert [livro.ordem for livro in LIVROS] == list(range(1, 67))


def test_osis_e_nomes_sao_unicos():
    assert len({livro.osis for livro in LIVROS}) == 66
    assert len({livro.nome for livro in LIVROS}) == 66


def test_osis_bate_com_o_dataset_do_openbible():
    """Se o mapa divergir do dado real, a integração quebra."""
    assert {livro.osis for livro in LIVROS} == OSIS_DO_DATASET


# ── a regra do acento: o bug que isto corrige ───────────────────────────────

def test_jo_e_joao_mas_jo_acentuado_e_o_livro_de_jo():
    assert resolver("Jo").nome == "João"
    assert resolver("jo").nome == "João"
    assert resolver("JO").nome == "João"
    assert resolver("Jó").nome == "Jó"
    assert resolver("jó").nome == "Jó"
    assert resolver("JÓ").nome == "Jó"
    assert resolver("Job").nome == "Jó"


def test_joao_por_extenso_e_joao():
    assert resolver("João").nome == "João"
    assert resolver("joao").nome == "João"
    assert resolver("João").osis == "John"


def test_acento_que_antes_derrubava_a_citacao():
    """`Êx` não resolvia: o mapa antigo só tinha `ex` e `êxodo`."""
    assert resolver("Êx").nome == "Êxodo"
    assert resolver("Êx").osis == "Exod"
    assert resolver("Ex").nome == "Êxodo"


def test_nomes_que_so_existem_sem_acento_resolvem_igual():
    assert resolver("Gênesis").nome == "Gênesis"
    assert resolver("Genesis").nome == "Gênesis"
    assert resolver("Isaias").nome == "Isaías"
    assert resolver("Isaías").nome == "Isaías"
    assert resolver("Efesios").nome == "Efésios"
    assert resolver("Amos").nome == "Amós"


def test_numero_com_espaco_e_caixa_variada():
    assert resolver("1 Co").osis == "1Cor"
    assert resolver("1co").osis == "1Cor"
    assert resolver("2 Ts").osis == "2Thess"
    assert resolver("3 jo").osis == "3John"
    assert resolver("1 Jo").nome == "1 João"
    assert resolver("1 Jó") is None  # "1 Jó" nao existe


def test_nomes_por_extenso_do_mapa_antigo_continuam_valendo():
    """Nada que o ALIASES antigo resolvia pode ter regredido."""
    antigos = {
        "joão": "João", "joao": "João", "salmo": "Salmos", "salmos": "Salmos",
        "gênesis": "Gênesis", "genesis": "Gênesis", "êxodo": "Êxodo",
        "exodo": "Êxodo", "mateus": "Mateus", "marcos": "Marcos",
        "lucas": "Lucas", "atos": "Atos", "romanos": "Romanos",
        "efésios": "Efésios", "efesios": "Efésios", "hebreus": "Hebreus",
        "tiago": "Tiago", "apocalipse": "Apocalipse", "isaías": "Isaías",
        "isaias": "Isaías", "jeremias": "Jeremias",
    }
    for abrev, esperado in antigos.items():
        achado = resolver(abrev)
        assert achado is not None, f"{abrev!r} deixou de resolver"
        assert achado.nome == esperado


def test_abreviacoes_do_mapa_antigo_continuam_valendo():
    """As 66 abreviações curtas que o LIVROS antigo aceitava."""
    antigas = [
        "gn", "ex", "lv", "nm", "dt", "js", "jz", "rt", "1sm", "2sm", "1rs",
        "2rs", "1cr", "2cr", "ed", "ne", "et", "sl", "pv", "ec", "ct", "is",
        "jr", "lm", "ez", "dn", "os", "jl", "am", "ob", "jn", "mq", "na", "hc",
        "sf", "ag", "zc", "ml", "mt", "mc", "lc", "at", "rm", "1co", "2co",
        "gl", "ef", "fp", "cl", "1ts", "2ts", "1tm", "2tm", "tt", "fm", "hb",
        "tg", "1pe", "2pe", "1jo", "2jo", "3jo", "jd", "ap", "joao",
    ]
    for abrev in antigas:
        assert resolver(abrev) is not None, f"{abrev!r} deixou de resolver"


# ── utilitários ────────────────────────────────────────────────────────────

def test_token_desconhecido_devolve_none():
    for lixo in ("", "   ", "xyz", "capitulo", "item", "12", "abc123"):
        assert resolver(lixo) is None


def test_por_osis_e_por_ordem():
    assert por_osis("John").nome == "João"
    assert por_osis("Job").nome == "Jó"
    assert por_osis("Gen").ordem == 1
    assert por_osis("NaoExiste") is None
    assert por_ordem(1).osis == "Gen"
    assert por_ordem(66).osis == "Rev"
    assert por_ordem(43).nome == "João"
    assert por_ordem(0) is None
    assert por_ordem(67) is None


def test_sem_acento():
    assert sem_acento("Êx") == "ex"
    assert sem_acento("Jó") == "jo"
    assert sem_acento("1 Coríntios") == "1 corintios"
    assert sem_acento("Gênesis") == "genesis"


# ── extração de referências (o caminho que a lição usa) ────────────────────

def test_extrair_nao_confunde_joao_com_jo():
    """O caso exato do bug: capítulo 21 cita 'Jo 3.16'."""
    assert EscrituraService.extrair_referencias("**Jo 3.16** — o amor de Deus") == [
        "João 3:16"
    ]
    assert EscrituraService.extrair_referencias("Jó 1.21 — nu saí do ventre") == [
        "Jó 1:21"
    ]
    # o mesmo capitulo:verso, mas em Jo — e o oposto do que o bug fazia
    assert EscrituraService.extrair_referencias("Jó 3.16") == ["Jó 3:16"]


def test_extrair_preserva_intervalo():
    assert EscrituraService.extrair_referencias("Êx 34.6-7") == ["Êxodo 34:6-7"]
    assert EscrituraService.extrair_referencias("Mt 28.19-20") == ["Mateus 28:19-20"]
    assert EscrituraService.extrair_referencias("1Co 13.4-7") == ["1 Coríntios 13:4-7"]


def test_extrair_remove_repeticao_e_ignora_lixo():
    texto = "Rm 3.23 e de novo Rm 3.23, mas capitulo 3.1 nao e referencia"
    assert EscrituraService.extrair_referencias(texto) == ["Romanos 3:23"]


def test_extrair_texto_vazio():
    assert EscrituraService.extrair_referencias("") == []
    assert EscrituraService.extrair_referencias(None) == []


def test_extrair_bloco_real_de_plano():
    """Trecho no formato exato dos planos (capitulo_01)."""
    trecho = """
### Passagens biblicas a memorizar

- [ ] **Mt 28.19-20** — Grande Comissao (ensinar tudo o que Jesus ordenou)
- [ ] **Sl 119.18** — "Desvenda os meus olhos para que eu contemple as maravilhas"
- [ ] **1Co 2.14** — Coisas espirituais se discernem espiritualmente
- [ ] **1Tm 6.3 / Tt 1.1** — "Ensino segundo a piedade"
"""
    assert EscrituraService.extrair_referencias(trecho) == [
        "Mateus 28:19-20",
        "Salmos 119:18",
        "1 Coríntios 2:14",
        "1 Timóteo 6:3",
        "Tito 1:1",
    ]
