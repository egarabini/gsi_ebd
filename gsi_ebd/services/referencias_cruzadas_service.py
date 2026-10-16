"""Passagens relacionadas de uma lição — referências cruzadas do OpenBible.

O QUE ISTO FAZ
--------------
Dado o plano de estudo, pega as passagens que ele cita, consulta a tabela
`ReferenciaCruzada` e devolve até `MAX_RELACIONADAS` passagens relacionadas — com
o TEXTO vindo do corpus local (ACF 2007), nunca do modelo.

CURADORIA (medida em `Diagnostico/referencias-cruzadas.md`)
----------------------------------------------------------
- **Piso de votos (`VOTOS_MINIMOS = 10`)**: os votos são um saldo e podem ser
  negativos (mínimo −86, mediana 3). Sem piso, uma relação *rejeitada* pela
  comunidade entraria na lição. Com votos ≥ 10 sobram 45.036 dos 344.799 pares
  (13%), e ainda assim 96,6% das citações dos planos têm candidato.
- **Teto de 5 por lição**: no corte de votos ≥ 10 a média era de 21,7 passagens
  relacionadas por citação. Exibir isso cru é pior que não exibir.
- **Rodízio entre as citações**: as 5 saem alternando entre os versículos que o
  plano cita, para o bloco não ficar dominado por um só. Cada citação contribui
  com a sua melhor antes de qualquer uma contribuir com a segunda.
- **Nada que o plano já cita**, e nada repetido.

LICENÇA
-------
O dado é CC-BY 4.0: a atribuição a OpenBible.info é **obrigatória** e vai no
próprio bloco renderizado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import reflex as rx
from sqlmodel import select

from ..models import ReferenciaCruzada
from ..utils.livros import Livro, por_osis
from .escritura_service import Citacao, EscrituraService, escritura

# Piso de votos: abaixo disso a relação é fraca ou rejeitada (ver o cabeçalho).
VOTOS_MINIMOS = 10
# Teto do bloco, por lição.
MAX_RELACIONADAS = 5
# Quantos versículos de um intervalo são exibidos (o resto vira "…").
MAX_VERSICULOS_DE_INTERVALO = 3

ATRIBUICAO = "referências cruzadas: OpenBible.info, CC-BY 4.0"

# 'Rom.8.5' | 'Rom.8.5-Rom.8.8' — as duas formas que existem no arquivo
# (conferido: 256.649 simples e 88.150 em intervalo, nenhuma outra).
RE_OSIS = re.compile(
    r"^([1-3]?[A-Za-z]+)\.(\d{1,3})\.(\d{1,3})"
    r"(?:-\s*([1-3]?[A-Za-z]+)\.(\d{1,3})\.(\d{1,3}))?$"
)


@dataclass(frozen=True)
class PassagemRelacionada:
    """Uma passagem sugerida, com a origem que a trouxe e quantos votos tem."""

    livro: Livro
    capitulo: int
    versiculo: int
    versiculo_fim: int
    votos: int
    origem: str

    @property
    def rotulo(self) -> str:
        fim = "" if self.versiculo_fim == self.versiculo else f"-{self.versiculo_fim}"
        return f"{self.livro.nome} {self.capitulo}:{self.versiculo}{fim}"

    @property
    def chave(self) -> Tuple[str, int, int, int]:
        return (self.livro.osis, self.capitulo, self.versiculo, self.versiculo_fim)

    def citacao(self) -> Citacao:
        return Citacao(
            livro=self.livro,
            capitulo=self.capitulo,
            versiculo=self.versiculo,
            versiculo_fim=self.versiculo_fim,
        )


# ── conversão (funções puras, é onde mora a lógica) ─────────────────────────

def chave_osis(citacao: Citacao) -> str:
    """A chave do lado "de" no dataset: `'John.3.16'`."""
    return f"{citacao.livro.osis}.{citacao.capitulo}.{citacao.versiculo}"


def parse_destino(bruto: str, origem: str, votos: int) -> Optional[PassagemRelacionada]:
    """`'Rom.8.5-Rom.8.8'` -> PassagemRelacionada. Ignora o que não reconhece."""
    m = RE_OSIS.match((bruto or "").strip())
    if not m:
        return None
    livro = por_osis(m.group(1))
    if livro is None:
        return None
    capitulo, versiculo = int(m.group(2)), int(m.group(3))
    fim = versiculo
    if m.group(4) is not None:
        # O intervalo repete livro e capítulo (`Rom.8.5-Rom.8.8`); se divergir,
        # é forma desconhecida: fica só o primeiro versículo, que é o seguro.
        if m.group(4) == m.group(1) and int(m.group(5)) == capitulo:
            fim = max(versiculo, int(m.group(6)))
    return PassagemRelacionada(
        livro=livro,
        capitulo=capitulo,
        versiculo=versiculo,
        versiculo_fim=fim,
        votos=votos,
        origem=origem,
    )


def selecionar(
    candidatos: Iterable[PassagemRelacionada],
    ja_citadas: Set[Tuple[str, int, int, int]] | None = None,
    maximo: int = MAX_RELACIONADAS,
) -> List[PassagemRelacionada]:
    """Até `maximo` passagens, em rodízio entre as citações de origem.

    Rodízio e não "as N mais votadas no geral": assim cada versículo que o plano
    cita contribui com a sua melhor relacionada antes de qualquer um contribuir
    com a segunda — o bloco fica representativo do capítulo, não de uma citação.
    """
    vistas: Set[Tuple[str, int, int, int]] = set(ja_citadas or ())
    por_origem: Dict[str, List[PassagemRelacionada]] = {}
    for candidato in sorted(candidatos, key=lambda p: -p.votos):
        if candidato.chave in vistas:
            continue
        por_origem.setdefault(candidato.origem, []).append(candidato)

    escolhidas: List[PassagemRelacionada] = []
    while len(escolhidas) < maximo:
        progrediu = False
        for origem in list(por_origem):
            fila = por_origem[origem]
            while fila:
                candidato = fila.pop(0)
                if candidato.chave in vistas:
                    continue
                vistas.add(candidato.chave)
                escolhidas.append(candidato)
                progrediu = True
                break
            if len(escolhidas) >= maximo:
                break
        if not progrediu:
            break
    return escolhidas


def renderizar(
    selecionadas: Sequence[PassagemRelacionada],
    texto_de: Callable[[PassagemRelacionada], str],
    atribuicao: str = ATRIBUICAO,
) -> str:
    """Monta o bloco markdown. Sem selecionadas, devolve vazio (nada a exibir).

    O título fica no cabeçalho do cartão da lição; aqui vai a atribuição, que é
    obrigação da licença CC-BY e não pode depender de onde o bloco é exibido.
    """
    if not selecionadas:
        return ""
    linhas = [f"> *{atribuicao}*\n"]
    for passagem in selecionadas:
        texto = (texto_de(passagem) or "").strip()
        linhas.append(f"> **{passagem.rotulo}** — {texto}" if texto else f"> **{passagem.rotulo}**")
    return "\n>\n".join(linhas)


# ── serviço (fala com o banco e com o corpus) ───────────────────────────────

class ReferenciasCruzadasService:
    """Degrada em silêncio: sem tabela, sem corpus ou sem candidato, devolve ""."""

    @staticmethod
    def candidatos(origens: Sequence[str], votos_minimos: int = VOTOS_MINIMOS) -> List[PassagemRelacionada]:
        """Consulta a tabela para cada chave de origem."""
        if not origens:
            return []
        achados: List[PassagemRelacionada] = []
        with rx.session() as session:
            linhas = session.exec(
                select(
                    ReferenciaCruzada.de_versiculo,
                    ReferenciaCruzada.para_versiculo,
                    ReferenciaCruzada.votos,
                )
                .where(ReferenciaCruzada.de_versiculo.in_(list(origens)))
                .where(ReferenciaCruzada.votos >= votos_minimos)
            ).all()
        for de, para, votos in linhas:
            passagem = parse_destino(para, origem=de, votos=votos)
            if passagem is not None:
                achados.append(passagem)
        return achados

    @staticmethod
    def _texto(passagem: PassagemRelacionada, servico: EscrituraService) -> str:
        """O texto vem do corpus; intervalo longo é cortado para o bloco não crescer."""
        versiculos = servico.buscar_citacao(passagem.citacao())
        if not versiculos:
            return ""
        textos = [v.texto for v in versiculos[:MAX_VERSICULOS_DE_INTERVALO] if v.texto]
        if not textos:
            return ""
        juntado = " ".join(textos)
        if len(versiculos) > MAX_VERSICULOS_DE_INTERVALO:
            juntado += " …"
        return juntado

    @classmethod
    def bloco(cls, plano_md: str, servico: EscrituraService | None = None) -> str:
        """O bloco de passagens relacionadas para o plano, ou "" se não houver."""
        try:
            citacoes = EscrituraService.extrair_citacoes(plano_md or "")
            if not citacoes:
                return ""
            servico = servico or escritura
            origens = [chave_osis(c) for c in citacoes[:6]]
            candidatos = cls.candidatos(origens)
            if not candidatos:
                return ""
            ja_citadas = {(c.livro.osis, c.capitulo, c.versiculo, c.versiculo_fim) for c in citacoes}
            selecionadas = selecionar(candidatos, ja_citadas=ja_citadas)
            return renderizar(selecionadas, lambda p: cls._texto(p, servico))
        except Exception:
            # Sem tabela carregada, sem banco ou sem corpus: a lição segue sem o
            # bloco. Mesma escolha do bloco de Escritura — e deliberada.
            return ""
