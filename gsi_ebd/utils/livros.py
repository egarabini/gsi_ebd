"""Mapa canônico dos 66 livros da Bíblia — fonte única da verdade.

POR QUE ESTE MÓDULO EXISTE
--------------------------
O projeto chegou a ter TRÊS mapas de livros, e eles se contradiziam. O pior caso
era "Jo": a convenção de abreviaturas dos estudos (AGENTS.md do DOUTRINAS_CRISTAS)
diz *Jo = João*, mas o mapa do `escritura_service` resolvia "jo" como **Jó**, o
livro. Como `Jó 3:16` existe de verdade, a lição exibia o versículo ERRADO — sem
erro nenhum em log. Medido: 17 citações erradas e 2 descartadas nos 34 planos.

Aqui ficam, por livro, a ordem canônica, o nome em português (como a lição exibe),
o código OSIS (a chave que o dataset de referências cruzadas do OpenBible usa) e as
abrevições aceitas.

A REGRA DO ACENTO
-----------------
A resolução tem duas camadas:

1. **chave exata** (com acento, quando houver): `"jo"` → João, `"jó"` → Jó;
2. **sem acento**, apenas para o que ainda não existe na camada 1.

Assim `"Jo"` continua sendo o evangelho de João e `"Jó"` continua sendo o livro de
Jó, sem que um atropele o outro — e `"Êx"`, que ninguém escreve por extenso nos
planos, resolve para Êxodo mesmo assim.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass


def tirar_acentos(texto: str) -> str:
    """Remove acentos PRESERVANDO a caixa: `'João'` -> `'Joao'`, `'Êx'` -> `'Ex'`.

    É o que o corpus precisa: ele grava `'Joao 3:16'`, não `'joao 3:16'`.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def sem_acento(texto: str) -> str:
    """Minúsculas e sem acento: `'Êx'` -> `'ex'`; `'Jó'` -> `'jo'`.

    É a chave de comparação de ABREVIATURAS (aceita `'JO'`, `'1 Co'`, `'Jó'`).
    Para o nome como o corpus grava, use `tirar_acentos` — a caixa importa lá.
    """
    return tirar_acentos(texto).lower()


@dataclass(frozen=True)
class Livro:
    """Um livro da Bíblia, com as identidades que o projeto precisa."""

    ordem: int
    osis: str  # chave do dataset de referências cruzadas (OpenBible)
    nome: str  # em português, com acento — é o que a lição exibe
    abreviacoes: tuple[str, ...]

    def __str__(self) -> str:
        return self.nome

    @property
    def nome_corpus(self) -> str:
        """Como o CORPUS grava o nome do livro: sem acento e sem espaço.

        É a chave do metadado `referencia` no ChromaDB (ver
        `load_biblia.py:230`), e portanto o que a busca exata precisa casar.
        Medido contra `PREFIXO_LIVRO`: 63 dos 66 saem da normalização do nome
        canônico (`João` → `Joao`, `Jó` → `Jo`); 3 têm grafia própria e estão
        no mapa de divergências abaixo.
        """
        return _NOME_CORPUS_DIVERGENTE.get(self.osis) or tirar_acentos(self.nome).replace(" ", "")

    def referencia_corpus(self, capitulo: int, versiculo: int) -> str:
        """A chave exata de um versículo no índice: `'Joao 3:16'`."""
        return f"{self.nome_corpus} {capitulo}:{versiculo}"


# Nomes que o corpus usa e que NÃO saem da normalização do nome canônico.
# Conferidos contra PREFIXO_LIVRO do load_biblia.py — são grafias legítimas,
# não erros: "Cantares" é o nome do livro, "Abdias" e "Filemon" são variantes
# correntes em português. Ver _openbible/comparar_nomes_corpus.py.
_NOME_CORPUS_DIVERGENTE = {
    "Song": "Cantares",
    "Obad": "Abdias",
    "Phlm": "Filemon",
}


# A ordem é a canônica (1..66). Os códigos OSIS são exatamente os que o dataset
# do OpenBible usa — conferidos contra os 66 códigos presentes no arquivo.
LIVROS: tuple[Livro, ...] = (
    Livro(1, "Gen", "Gênesis", ("gn", "gênesis", "genesis")),
    Livro(2, "Exod", "Êxodo", ("ex", "êx", "exo", "êxo", "êxodo", "exodo")),
    Livro(3, "Lev", "Levítico", ("lv", "lev", "levitico", "levítico")),
    Livro(4, "Num", "Números", ("nm", "num", "numeros", "números")),
    Livro(5, "Deut", "Deuteronômio", ("dt", "deut", "deuteronomio", "deuteronômio")),
    Livro(6, "Josh", "Josué", ("js", "jos", "josue", "josué")),
    Livro(7, "Judg", "Juízes", ("jz", "juiz", "juizes", "juízes")),
    Livro(8, "Ruth", "Rute", ("rt", "rute")),
    Livro(9, "1Sam", "1 Samuel", ("1sm", "1sam")),
    Livro(10, "2Sam", "2 Samuel", ("2sm", "2sam")),
    Livro(11, "1Kgs", "1 Reis", ("1rs",)),
    Livro(12, "2Kgs", "2 Reis", ("2rs",)),
    Livro(13, "1Chr", "1 Crônicas", ("1cr", "1cronicas", "1crônicas")),
    Livro(14, "2Chr", "2 Crônicas", ("2cr", "2cronicas", "2crônicas")),
    Livro(15, "Ezra", "Esdras", ("ed", "esd", "esdras")),
    Livro(16, "Neh", "Neemias", ("ne", "neemias")),
    Livro(17, "Esth", "Ester", ("et", "est", "ester")),
    # ATENÇÃO: "jo" NÃO entra aqui. Na convenção dos estudos, "Jo" é João (livro 43).
    # O livro de Jó só se escreve com acento.
    Livro(18, "Job", "Jó", ("jó", "job")),
    Livro(19, "Ps", "Salmos", ("sl", "salmo", "salmos")),
    Livro(20, "Prov", "Provérbios", ("pv", "prov", "proverbios", "provérbios")),
    Livro(21, "Eccl", "Eclesiastes", ("ec", "eclesiastes")),
    Livro(22, "Song", "Cântico dos Cânticos", ("ct", "cantares")),
    Livro(23, "Isa", "Isaías", ("is", "isa", "isaias", "isaías")),
    Livro(24, "Jer", "Jeremias", ("jr", "jer", "jeremias")),
    Livro(25, "Lam", "Lamentações", ("lm", "lamentacoes", "lamentações")),
    Livro(26, "Ezek", "Ezequiel", ("ez", "ezequiel")),
    Livro(27, "Dan", "Daniel", ("dn", "dan", "daniel")),
    Livro(28, "Hos", "Oséias", ("os", "oseias", "oséias")),
    Livro(29, "Joel", "Joel", ("jl", "joel")),
    Livro(30, "Amos", "Amós", ("am", "amos", "amós")),
    Livro(31, "Obad", "Obadias", ("ob", "obadias")),
    Livro(32, "Jonah", "Jonas", ("jn", "jonas")),
    Livro(33, "Mic", "Miquéias", ("mq", "miqueias", "miquéias")),
    Livro(34, "Nah", "Naum", ("na", "naum")),
    Livro(35, "Hab", "Habacuque", ("hc", "hab", "habacuque")),
    Livro(36, "Zeph", "Sofonias", ("sf", "sof", "sofonias")),
    Livro(37, "Hag", "Ageu", ("ag", "ageu")),
    Livro(38, "Zech", "Zacarias", ("zc", "zac", "zacarias")),
    Livro(39, "Mal", "Malaquias", ("ml", "mal", "malaquias")),
    Livro(40, "Matt", "Mateus", ("mt", "mateus")),
    Livro(41, "Mark", "Marcos", ("mc", "marcos")),
    Livro(42, "Luke", "Lucas", ("lc", "lucas")),
    # "Jo" = João, por convenção do estudo. Ver a nota no livro 18.
    Livro(43, "John", "João", ("jo", "joao", "joão")),
    Livro(44, "Acts", "Atos", ("at", "atos")),
    Livro(45, "Rom", "Romanos", ("rm", "rom", "romanos")),
    Livro(46, "1Cor", "1 Coríntios", ("1co", "1cor", "1corintios", "1coríntios")),
    Livro(47, "2Cor", "2 Coríntios", ("2co", "2cor", "2corintios", "2coríntios")),
    Livro(48, "Gal", "Gálatas", ("gl", "gal", "galatas", "gálatas")),
    Livro(49, "Eph", "Efésios", ("ef", "efesios", "efésios")),
    Livro(50, "Phil", "Filipenses", ("fp", "fil", "filipenses")),
    Livro(51, "Col", "Colossenses", ("cl", "col", "colossenses")),
    Livro(52, "1Thess", "1 Tessalonicenses", ("1ts",)),
    Livro(53, "2Thess", "2 Tessalonicenses", ("2ts",)),
    Livro(54, "1Tim", "1 Timóteo", ("1tm", "1tim", "1timoteo", "1timóteo")),
    Livro(55, "2Tim", "2 Timóteo", ("2tm", "2tim", "2timoteo", "2timóteo")),
    Livro(56, "Titus", "Tito", ("tt", "tito")),
    Livro(57, "Phlm", "Filemom", ("fm", "filemom", "filemon")),
    Livro(58, "Heb", "Hebreus", ("hb", "heb", "hebreus")),
    Livro(59, "Jas", "Tiago", ("tg", "tiago")),
    Livro(60, "1Pet", "1 Pedro", ("1pe", "1pedro")),
    Livro(61, "2Pet", "2 Pedro", ("2pe", "2pedro")),
    Livro(62, "1John", "1 João", ("1jo", "1joao", "1joão")),
    Livro(63, "2John", "2 João", ("2jo", "2joao", "2joão")),
    Livro(64, "3John", "3 João", ("3jo", "3joao", "3joão")),
    Livro(65, "Jude", "Judas", ("jd", "judas")),
    Livro(66, "Rev", "Apocalipse", ("ap", "apocalipse")),
)


def _normalizar(token: str) -> str:
    return token.strip().lower().replace(" ", "")


_EXATO: dict[str, Livro] = {}
_POR_OSIS: dict[str, Livro] = {}

for _livro in LIVROS:
    if _livro.osis in _POR_OSIS:
        raise ValueError(f"OSIS duplicado: {_livro.osis}")
    _POR_OSIS[_livro.osis] = _livro
    for _abrev in _livro.abreviacoes:
        _chave = _normalizar(_abrev)
        _dono = _EXATO.get(_chave)
        if _dono is not None and _dono is not _livro:
            raise ValueError(
                f"abreviacao {_abrev!r} reivindicada por {_dono.nome} e {_livro.nome}"
            )
        _EXATO[_chave] = _livro

# Segunda camada: versoes sem acento que ainda nao existem como chave exata.
# E aqui que "Jó" (-> "jo") NAO rouba "Jo": "jo" ja e chave exata de Joao.
_SEM_ACENTO: dict[str, Livro] = {}
for _livro in LIVROS:
    for _abrev in _livro.abreviacoes:
        _chave = sem_acento(_normalizar(_abrev))
        if _chave in _EXATO:
            continue  # a camada exata manda
        _dono = _SEM_ACENTO.get(_chave)
        if _dono is not None and _dono is not _livro:
            raise ValueError(
                f"abreviacao sem acento {_chave!r} ambigua: "
                f"{_dono.nome} e {_livro.nome}"
            )
        _SEM_ACENTO[_chave] = _livro


def resolver(token: str) -> Livro | None:
    """Abreviação ou nome -> Livro. Aceita `'Jo'`, `'Jó'`, `'Êx'`, `'1 Co'`, `'João'`."""
    if not token or not token.strip():
        return None
    chave = _normalizar(token)
    return _EXATO.get(chave) or _SEM_ACENTO.get(sem_acento(chave))


def por_osis(osis: str) -> Livro | None:
    """Código OSIS (`'John'`) -> Livro."""
    return _POR_OSIS.get(osis)


def por_ordem(ordem: int) -> Livro | None:
    """Posição canônica (1..66) -> Livro."""
    if 1 <= ordem <= len(LIVROS):
        return LIVROS[ordem - 1]
    return None
