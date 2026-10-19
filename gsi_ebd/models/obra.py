"""Obra (a fonte), seus capítulos e os adendos.

Modelo definido pelo Eduardo em 2026-10-16 (ver `Diagnostico/plano-bibliotecas.md`):

    OBRA (livro, coletânea ou condensado de vários livros)
      + CAPÍTULOS  divisões da obra, só para o arquivo não ficar enorme
      + ADENDOS    notas do Administrador E do Revisor (da obra e/ou de um capítulo)
        └─ juntos, definem a BASE do estudo

O **ESTUDO** é outro artefato e vem nas fases seguintes: seus capítulos não
correspondem necessariamente aos da obra (um capítulo da obra pode gerar vários
do estudo), e o mapa entre os dois será uma tabela própria.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint


class Doutrina(SQLModel, table=True):
    """Tradição doutrinária — **cadastrável e sem bloqueio**.

    Serve de orientação ao coordenador na hora de escolher estudos. Decisão do
    Eduardo: não restringe acesso, porque ele pode querer usar um estudo de outra
    tradição e registrar as ressalvas nos comentários.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    descricao: str = Field(default="")
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class Obra(SQLModel, table=True):
    """A FONTE. Não é o estudo que o aluno faz."""

    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str = Field(index=True)
    tipo: str = Field(default="livro")  # livro|coletanea|condensado
    descricao: str = Field(default="")
    doutrina_id: Optional[int] = Field(default=None, foreign_key="doutrina.id")

    # De onde o texto veio, para reprocessar sem adivinhar.
    origem: str = Field(default="")

    status: str = Field(default="em_revisao")
    disponibilidade: str = Field(default="aberta")
    versao_liberada_id: Optional[int] = Field(default=None, foreign_key="obraversao.id")
    fonte_id: Optional[str] = Field(default=None, index=True)
    updated_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class ObraCapitulo(SQLModel, table=True):
    """Divisão da OBRA — **não** é o capítulo do estudo."""

    id: Optional[int] = Field(default=None, primary_key=True)
    obra_id: int = Field(foreign_key="obra.id", index=True)
    ordem: int
    titulo: str = Field(default="")
    conteudo_md: str = Field(default="")
    arquivo: str = Field(default="")


class Adendo(SQLModel, table=True):
    """Nota do Administrador/Revisor que, com o capítulo da obra, define a base.

    `obra_capitulo_id` nulo significa adendo da OBRA inteira (`ADO-01`); com
    valor, é o adendo daquele capítulo (`ADO-01.03`).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    obra_id: int = Field(foreign_key="obra.id", index=True)
    obra_capitulo_id: Optional[int] = Field(
        default=None, foreign_key="obracapitulo.id", index=True
    )
    codigo: str = Field(default="")  # ADO-01 / ADO-01.03
    titulo: str = Field(default="")
    texto: str = Field(default="")
    ambiente_id: Optional[int] = Field(default=None, foreign_key="ambiente.id", index=True)
    autor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: Optional[datetime] = Field(default=None)


class ObraVersao(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("obra_id", "numero"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    obra_id: int = Field(foreign_key="obra.id", index=True)
    numero: int = Field(default=1)
    rodada: int = Field(default=0)
    status: str = Field(default="em_revisao")
    conteudo_hash: str = Field(default="")
    parecer: str = Field(default="")
    ajustes_propostos: str = Field(default="[]")
    revisor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    revisado_em: Optional[datetime] = Field(default=None)
    hash_visto: str = Field(default="")
    ajustes_descritos: str = Field(default="")
    admin_id: Optional[int] = Field(default=None, foreign_key="user.id")
    liberada_em: Optional[datetime] = Field(default=None)
    hash_liberado: str = Field(default="")
    created_at: Optional[datetime] = Field(default=None)


class ObraVersaoCapitulo(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("versao_id", "momento", "rodada", "ordem"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="obraversao.id", index=True)
    momento: str
    rodada: int
    ordem: int
    titulo: str = Field(default="")
    conteudo_md: str = Field(default="")
    item_hash: str = Field(default="")


class ObraVersaoAdendo(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("versao_id", "momento", "rodada", "codigo"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="obraversao.id", index=True)
    momento: str
    rodada: int
    codigo: str = Field(default="")
    titulo: str = Field(default="")
    texto: str = Field(default="")
    item_hash: str = Field(default="")


class ObraVersaoEvento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    versao_id: int = Field(foreign_key="obraversao.id", index=True)
    tipo: str
    autor_id: int = Field(foreign_key="user.id")
    quando: datetime
    detalhe: str = Field(default="{}")


class VinculoObra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ambiente_id: int = Field(foreign_key="ambiente.id", index=True)
    obra_id: int = Field(foreign_key="obra.id", index=True)
    versao_id: int = Field(foreign_key="obraversao.id", index=True)
    coordenador_id: int = Field(foreign_key="user.id")
    ativo: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)
