"""Avaliador de respostas abertas — parecer PRELIMINAR da IA.

FECHA O CICLO DO PRODUTO
-----------------------
O instrutor humano nao pode ser substituido: e ele que conhece o aluno. Mas ele
nao precisa comecar do zero. Este servico produz um parecer PRELIMINAR sobre a
resposta aberta; o instrutor le, aceita, ajusta ou descarta, e so entao o
parecer chega ao aluno.

Direcao do fluxo:
    aluno responde -> IA sugere -> INSTRUTOR confirma -> aluno recebe

A IA nunca fala direto com o aluno. Isso preserva o que o modelo SGI7 tem de
melhor (o cuidado humano) e usa a IA apenas para reduzir o esforco do instrutor.

O texto biblico de apoio vem do RAG local (escritura_service), nunca do modelo —
mesmo principio que vale para a licao.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

SISTEMA = """Você é um assistente pedagógico que apoia INSTRUTORES de estudo bíblico.
Sua tarefa é preparar um PARECER PRELIMINAR sobre a resposta escrita de um aluno.

Regras que você NUNCA quebra:
1. NÃO invente versículos nem cite texto bíblico de memória. Use apenas as
   passagens que receber no contexto. Se não houver passagem, não cite nenhuma.
2. NÃO julgue a fé, a sinceridade ou a vida espiritual do aluno. Avalie apenas a
   resposta escrita, em relação ao que a pergunta pede.
3. Seja encorajador e específico. Aponte o que está bom e o que faltou.
4. O parecer será lido pelo instrutor ANTES de chegar ao aluno — escreva para o
   instrutor, em terceira pessoa, de forma que ele possa editar e enviar.

Responda EXATAMENTE neste formato, sem nada antes ou depois:
ADERENCIA: <aderente|parcial|insuficiente>
COMENTARIO: <2 a 4 frases, em português brasileiro, sobre a resposta do aluno>
SUGESTAO: <uma pergunta ou orientação para o instrutor devolver ao aluno>
"""


@dataclass
class Parecer:
    aderencia: str = "indefinido"      # aderente | parcial | insuficiente
    comentario: str = ""
    sugestao: str = ""
    disponivel: bool = False           # False = IA fora do ar (o instrutor escreve)
    erro: str = ""


class AvaliadorService:
    """Chama o LLM local. Degrada em silencio se o Ollama nao estiver no ar."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    # ── Ollama por HTTP direto (sem depender de langchain) ──────────────────
    def _chamar(self, prompt: str, timeout: int = 120) -> Optional[str]:
        import json
        import urllib.request
        try:
            corpo = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SISTEMA},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/chat", data=corpo,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = json.loads(r.read().decode("utf-8", "replace"))
            return (dados.get("message") or {}).get("content") or dados.get("response") or ""
        except Exception:
            return None

    @staticmethod
    def _extrair(texto: str) -> Parecer:
        ad = re.search(r"ADERENCIA:\s*(.+)", texto, re.I)
        co = re.search(r"COMENTARIO:\s*(.+?)(?=\nSUGESTAO:|\Z)", texto, re.I | re.S)
        su = re.search(r"SUGESTAO:\s*(.+)", texto, re.I | re.S)
        p = Parecer(disponivel=True)
        if ad:
            bruto = ad.group(1).strip().lower()
            p.aderencia = next((x for x in ("aderente", "parcial", "insuficiente") if x in bruto),
                               "indefinido")
        if co:
            p.comentario = re.sub(r"\s+", " ", co.group(1)).strip()
        if su:
            p.sugestao = re.sub(r"\s+", " ", su.group(1)).strip()
        return p

    def avaliar(self, pergunta: str, resposta: str, contexto: str = "",
                referencia_biblica: str = "") -> Parecer:
        """Parecer preliminar sobre a resposta. Nunca levanta excecao."""
        if not (resposta or "").strip():
            return Parecer(comentario="O aluno não escreveu resposta.",
                           sugestao="Vale perguntar ao aluno o que ele entendeu da lição.",
                           disponivel=True)
        partes = [
            f"PERGUNTA FEITA AO ALUNO:\n{pergunta}",
            f"RESPOSTA DO ALUNO:\n{resposta}",
        ]
        if contexto:
            partes.append(f"TRECHO DA LIÇÃO (contexto do que era esperado):\n{contexto[:2000]}")
        if referencia_biblica:
            partes.append(f"PASSAGENS DO CORPUS (use apenas estas, não invente outras):\n"
                          f"{referencia_biblica[:1500]}")
        else:
            partes.append("PASSAGENS DO CORPUS: (nenhuma disponível — não cite versículos)")
        partes.append("Gere o parecer preliminar no formato pedido.")
        saida = self._chamar("\n\n".join(partes))
        if saida is None:
            return Parecer(
                disponivel=False,
                erro="Ollama não respondeu",
                comentario="",
                sugestao="",
            )
        return self._extrair(saida)


avaliador = AvaliadorService()
