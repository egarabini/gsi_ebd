"""Escritura verificada — ponte entre a plataforma e o RAG biblico.

OBSERVACAO DE ARQUITETURA
-------------------------
Ate agora a plataforma nao usava IA nenhuma: `AIService`, `ExplainerAgent`,
`TutorAgent`, `EvaluatorAgent` e `BibleService` existiam no codigo e nunca eram
chamados. E o `BibleService` dependia de uma API externa (bible-api.com), o que
traz dois problemas: depende de rede e o texto nao e verificavel localmente.

O projeto PASTOR_IA ja tem um RAG biblico funcionando: 31.102 versiculos da
Almeida Corrigida Fiel de 2007 (com os comentarios de Matthew Henry) indexados
no ChromaDB, colecao `biblia_pt_br`, com benchmark medido.

Este servico e a PONTE: traz o texto biblico do RAG local para dentro da licao.

Principio: o texto vem do corpus indexado, nunca do modelo. O LLM, quando
consultado, recebe a Escritura ja recuperada e e instruido a NAO acrescentar
texto biblico por conta propria — e assim que se evita alucinacao em conteudo
doutrinario.

Degradacao graciosa: se o ChromaDB nao estiver no ar (ou as dependencias nao
estiverem instaladas), o servico devolve vazio em vez de quebrar a licao.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from ..utils.livros import Livro, resolver

# ── Configuracao (mesmas chaves que o PASTOR_IA usa) ────────────────────────
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION_NAME = os.getenv("BIBLIA_COLLECTION", "biblia_pt_br")
# Embedding: nao passamos embedding_function na consulta, entao o chromadb usa o
# DefaultEmbeddingFunction dele (ONNXMiniLM_L6_V2, 384 dims).
#
# CORRECAO DE ENTENDIMENTO: o chromadb calcula o vetor NO CLIENTE, nao no
# servidor — "nao passar embedding_function" nao significa "o servidor resolve",
# significa "o cliente usa o modelo padrao". Isso importa porque a carga do corpus
# tem de usar EXATAMENTE o mesmo modelo: com modelos diferentes o indice e a
# consulta ficam em espacos vetoriais distintos, e como ambos tem 384 dimensoes
# nao ha erro nenhum — so similaridade sem sentido.
# A carga e o gsi_ebd/scripts/... usam PASTOR_IA/rag/biblia/load_biblia.py, que
# foi alinhado ao DefaultEmbeddingFunction por causa disto.
RAG_TOP_K = 5
RAG_SCORE_MIN = 0.55
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Livros: fonte unica e canonica em gsi_ebd/utils/livros.py.
#
# Aqui existia um mapa proprio, e ele era o bug: resolvia "jo" como Jo (o livro),
# enquanto a convencao de abreviaturas dos estudos (AGENTS.md do DOUTRINAS_CRISTAS)
# usa Jo = Joao. Como Jo 3:16 existe, a licao pedia o versiculo errado e recebia
# texto errado, sem erro nenhum. Medido nos 34 planos: 17 citacoes erradas e 2
# descartadas. Ver Diagnostico/referencias-cruzadas.md.

# "Rm 3.23", "1Co 13.4-7", "João 3:16", "Sl 119.18"
RE_REF = re.compile(
    r"\b((?:[1-3]\s*)?[A-Za-zÀ-ÿ]{2,12})\s*(\d{1,3})\s*[.:]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?"
)


@dataclass
class Versiculo:
    referencia: str
    texto: str
    score: float = 0.0


@dataclass
class Citacao:
    """Uma referencia citada no plano: livro + capitulo + versiculo(s).

    Existe para separar duas coisas que estavam misturadas: *achar* a passagem
    (igualdade, por metadado) e *buscar por assunto* (semelhanca, por embedding).
    """

    livro: Livro
    capitulo: int
    versiculo: int
    versiculo_fim: int = 0

    def __post_init__(self) -> None:
        if not self.versiculo_fim:
            self.versiculo_fim = self.versiculo

    @property
    def texto(self) -> str:
        """Como a citacao aparece para o leitor: `'Mt 28:19-20'` — aqui, por extenso."""
        fim = "" if self.versiculo_fim == self.versiculo else f"-{self.versiculo_fim}"
        return f"{self.livro.nome} {self.capitulo}:{self.versiculo}{fim}"

    def chaves_corpus(self, maximo: int = 12) -> List[str]:
        """As chaves EXATAS do indice (`'Joao 3:16'`).

        Intervalo longo e cortado em `maximo` versiculos: a licao exibe no maximo
        seis passagens, entao varrer um salmo inteiro so custaria tempo.
        """
        fim = min(self.versiculo_fim, self.versiculo + maximo - 1)
        return [
            self.livro.referencia_corpus(self.capitulo, v)
            for v in range(self.versiculo, fim + 1)
        ]


@dataclass
class EscrituraService:
    """Recupera Escritura do corpus local. Nunca inventa texto biblico."""

    _colecao: object = field(default=None, repr=False)
    _indisponivel: bool = field(default=False, repr=False)

    # ── conexao (uma vez por processo) ──────────────────────────────────────
    def _conectar(self):
        if self._colecao is not None or self._indisponivel:
            return self._colecao
        try:
            import chromadb

            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            # sem embedding_function: o CLIENTE usa o DefaultEmbeddingFunction
            # (o servidor nao vetoriza nada). A colecao precisa ter sido criada
            # com esse mesmo modelo — ver o comentario no topo do arquivo.
            self._colecao = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            # sem ChromaDB no ar: a licao continua funcionando, so sem Escritura citada
            self._indisponivel = True
            self._colecao = None
        return self._colecao

    @property
    def disponivel(self) -> bool:
        return self._conectar() is not None

    # ── extracao de referencias do plano de estudo ──────────────────────────
    @staticmethod
    def extrair_citacoes(texto: str) -> List[Citacao]:
        """Encontra as referencias biblicas do texto, ja resolvidas em livro.

        Aceita a convencao do estudo: `'Rm 3.23'`, `'1Co 13.4-7'`, `'Jo 3.16'`
        (Joao), `'Jó 1.21'` (o livro de Jo) e `'Êx 34.6-7'` (com acento).
        """
        achadas: List[Citacao] = []
        vistas: set = set()
        for m in RE_REF.finditer(texto or ""):
            bruto, cap, v1, v2 = m.group(1), m.group(2), m.group(3), m.group(4)
            livro = resolver(bruto)
            if livro is None:
                continue
            citacao = Citacao(
                livro=livro,
                capitulo=int(cap),
                versiculo=int(v1),
                versiculo_fim=int(v2 or v1),
            )
            if citacao.texto not in vistas:
                vistas.add(citacao.texto)
                achadas.append(citacao)
        return achadas

    @staticmethod
    def extrair_referencias(texto: str) -> List[str]:
        """As mesmas citacoes, como texto: `['Rm 3:23', '1Co 13:4-7']`."""
        return [c.texto for c in EscrituraService.extrair_citacoes(texto)]

    # ── busca ───────────────────────────────────────────────────────────────
    def buscar(self, consulta: str, n: int = RAG_TOP_K) -> List[Versiculo]:
        """Busca SEMANTICA por assunto, em texto livre.

        Serve para perguntar "onde a Biblia fala disso?". NAO serve para achar
        uma referencia: para isso e `buscar_citacao`, por igualdade.
        """
        col = self._conectar()
        if col is None or not consulta.strip():
            return []
        try:
            r = col.query(query_texts=[consulta], n_results=n)
        except Exception:
            return []
        docs = (r.get("documents") or [[]])[0]
        metas = (r.get("metadatas") or [[]])[0]
        dists = (r.get("distances") or [[]])[0]
        out: List[Versiculo] = []
        for i, doc in enumerate(docs):
            dist = dists[i] if i < len(dists) else 1.0
            score = 1.0 - float(dist)
            if score < RAG_SCORE_MIN:
                continue
            meta = metas[i] if i < len(metas) else {}
            ref = ""
            if isinstance(meta, dict):
                ref = meta.get("referencia") or ""
                if not ref:
                    livro, cap, ver = meta.get("livro"), meta.get("capitulo"), meta.get("versiculo")
                    ref = f"{livro} {cap}:{ver}" if livro else ""
            out.append(Versiculo(referencia=ref, texto=(doc or "").strip(), score=round(score, 3)))
        return out

    def buscar_citacao(self, citacao: Citacao) -> List[Versiculo]:
        """Busca EXATA por metadado — igualdade, sem embedding e sem corte de score.

        Antes isto era uma busca semantica usando a REFERENCIA como consulta, e o
        resultado era versiculo errado: `'João 3:16'` devolvia Mateus 4:12 (0.647)
        e Joao 4:1 (0.630) — os dois acima do corte de 0.55, prontos para aparecer
        na licao como se fossem a citacao. Referencia se acha por igualdade; a
        semelhanca fica para `buscar()`.

        Em caso de falha devolve vazio: e melhor a licao ficar sem o bloco de
        Escritura do que mostra-lo com o versiculo trocado.
        """
        col = self._conectar()
        if col is None:
            return []
        out: List[Versiculo] = []
        for chave in citacao.chaves_corpus():
            try:
                r = col.get(where={"referencia": chave})
            except Exception:
                continue
            docs = r.get("documents") or []
            metas = r.get("metadatas") or []
            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                referencia = ""
                if isinstance(meta, dict):
                    referencia = meta.get("referencia") or ""
                out.append(
                    Versiculo(
                        referencia=referencia or chave,
                        texto=(doc or "").strip(),
                        score=1.0,  # igualdade, nao similaridade
                    )
                )
        return out

    def buscar_referencias(self, citacoes: List[Citacao]) -> List[Versiculo]:
        """O texto das referencias citadas no plano; vem do corpus, por igualdade."""
        vistos, out = set(), []
        for citacao in citacoes[:6]:
            for v in self.buscar_citacao(citacao):
                if v.referencia and v.referencia not in vistos:
                    vistos.add(v.referencia)
                    out.append(v)
            if len(out) >= 6:
                break
        return out

    # ── contexto pronto para exibir na licao ────────────────────────────────
    def contexto_da_licao(self, plano_md: str, pergunta: str = "") -> str:
        """Monta o bloco de Escritura (markdown) para a licao.

        Recupera primeiro as referencias citadas no plano e, se houver pergunta,
        complementa com uma busca semantica por ela.
        """
        if not self.disponivel:
            return ""
        versiculos = self.buscar_referencias(self.extrair_citacoes(plano_md))
        if pergunta:
            for v in self.buscar(pergunta, n=3):
                if v.referencia and all(x.referencia != v.referencia for x in versiculos):
                    versiculos.append(v)
        if not versiculos:
            return ""
        linhas = ["> **Escritura** *(texto do corpus local — Almeida Corrigida Fiel)*\n"]
        for v in versiculos[:6]:
            rotulo = v.referencia or "(referência não identificada)"
            linhas.append(f"> **{rotulo}** — {v.texto}")
        return "\n>\n".join(linhas)


# instancia unica reaproveitada pelo processo
escritura = EscrituraService()
