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

# ── Configuracao (mesmas chaves que o PASTOR_IA usa) ────────────────────────
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION_NAME = os.getenv("BIBLIA_COLLECTION", "biblia_pt_br")
# Embedding: usamos o PADRAO DO SERVIDOR ChromaDB (ONNXMiniLM_L6_V2), nao o
# sentence-transformers do PASTOR_IA. Motivo: sentence-transformers arrasta o
# torch (~2 GB) para dentro da imagem da aplicacao. Como a colecao usa o
# embedding padrao, o servidor calcula os vetores e o cliente so envia texto.
# IMPORTANTE: app e carga do corpus precisam usar O MESMO embedding.
RAG_TOP_K = 5
RAG_SCORE_MIN = 0.55
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Livros em portugues, como aparecem no plano de estudo (abreviacoes da CONVENTIONS.md)
LIVROS = {
    "gn": "Gênesis", "ex": "Êxodo", "lv": "Levítico", "nm": "Números", "dt": "Deuteronômio",
    "js": "Josué", "jz": "Juízes", "rt": "Rute", "1sm": "1 Samuel", "2sm": "2 Samuel",
    "1rs": "1 Reis", "2rs": "2 Reis", "1cr": "1 Crônicas", "2cr": "2 Crônicas",
    "ed": "Esdras", "ne": "Neemias", "et": "Ester", "jo": "Jó", "sl": "Salmos",
    "pv": "Provérbios", "ec": "Eclesiastes", "ct": "Cantares", "is": "Isaías",
    "jr": "Jeremias", "lm": "Lamentações", "ez": "Ezequiel", "dn": "Daniel",
    "os": "Oséias", "jl": "Joel", "am": "Amós", "ob": "Obadias", "jn": "Jonas",
    "mq": "Miquéias", "na": "Naum", "hc": "Habacuque", "sf": "Sofonias",
    "ag": "Ageu", "zc": "Zacarias", "ml": "Malaquias",
    "mt": "Mateus", "mc": "Marcos", "lc": "Lucas", "joao": "João", "at": "Atos",
    "rm": "Romanos", "1co": "1 Coríntios", "2co": "2 Coríntios", "gl": "Gálatas",
    "ef": "Efésios", "fp": "Filipenses", "cl": "Colossenses",
    "1ts": "1 Tessalonicenses", "2ts": "2 Tessalonicenses", "1tm": "1 Timóteo",
    "2tm": "2 Timóteo", "tt": "Tito", "fm": "Filemom", "hb": "Hebreus",
    "tg": "Tiago", "1pe": "1 Pedro", "2pe": "2 Pedro", "1jo": "1 João",
    "2jo": "2 João", "3jo": "3 João", "jd": "Judas", "ap": "Apocalipse",
}
# nomes escritos por extenso que aparecem nos planos
ALIASES = {
    "joão": "João", "joao": "João", "salmo": "Salmos", "salmos": "Salmos",
    "gênesis": "Gênesis", "genesis": "Gênesis", "êxodo": "Êxodo", "exodo": "Êxodo",
    "mateus": "Mateus", "marcos": "Marcos", "lucas": "Lucas", "atos": "Atos",
    "romanos": "Romanos", "efésios": "Efésios", "efesios": "Efésios",
    "hebreus": "Hebreus", "tiago": "Tiago", "apocalipse": "Apocalipse",
    "isaías": "Isaías", "isaias": "Isaías", "jeremias": "Jeremias",
}

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
            # sem embedding_function: o SERVIDOR usa o padrao dele ao receber
            # texto puro. Isso mantem a imagem leve e a query coerente com o
            # indice, desde que a colecao tenha sido criada com o mesmo padrao.
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
    def extrair_referencias(texto: str) -> List[str]:
        """Encontra referencias biblicas (ex.: 'Rm 3.23', '1Co 13.4-7') no texto."""
        achadas: List[str] = []
        for m in RE_REF.finditer(texto or ""):
            bruto, cap, v1, v2 = m.group(1), m.group(2), m.group(3), m.group(4)
            chave = bruto.lower().replace(" ", "")
            livro = LIVROS.get(chave) or ALIASES.get(bruto.lower())
            if not livro:
                continue
            ref = f"{livro} {cap}:{v1}" + (f"-{v2}" if v2 else "")
            if ref not in achadas:
                achadas.append(ref)
        return achadas

    # ── busca ───────────────────────────────────────────────────────────────
    def buscar(self, consulta: str, n: int = RAG_TOP_K) -> List[Versiculo]:
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

    def buscar_referencias(self, referencias: List[str]) -> List[Versiculo]:
        """Busca cada referencia citada no plano; o texto vem do corpus."""
        vistos, out = set(), []
        for ref in referencias[:6]:
            for v in self.buscar(ref, n=2):
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
        versiculos = self.buscar_referencias(self.extrair_referencias(plano_md))
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
