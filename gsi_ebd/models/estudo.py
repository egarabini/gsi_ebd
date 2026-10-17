"""Estudo aplicavel e seus capitulos — o artefato que o aluno percorre.

Modelo definido pelo Eduardo em 2026-10-16 (ver
`documentacao/dem/DEM-202610-001-estudo-capitulos/planner/design.md`):

    OBRA (a fonte) + ADENDOS  ->  ESTUDO (o aplicavel)  ->  CAPITULOS do estudo

Os capitulos do ESTUDO nao correspondem aos da OBRA: o mapa entre os dois e uma
tabela propria (N:N), porque um capitulo da obra pode gerar varios do estudo e
varios da obra podem alimentar um so.

Esta DEM cria o modelo EM PARALELO ao que ja existe: `Study`/`StudyVersion`
continuam servindo a licao do aluno, e a migracao e outra DEM.
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from .study import StudyStatus


class Estudo(SQLModel, table=True):
    """O material aplicavel, nascido de uma OBRA.

    `status` comeca em RASCUNHO e so muda com aprovacao assinada (ADR-011). Reusa
    o enum do catalogo de proposito: e o mesmo ciclo de vida (rascunho -> proposto
    -> em_revisao -> aprovado), e um enum paralelo so criaria taxonomia duplicada.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    obra_id: int = Field(foreign_key="obra.id", index=True)
    titulo: str = Field(index=True)
    descricao: str = Field(default="")
    doutrina_id: Optional[int] = Field(default=None, foreign_key="doutrina.id")

    status: str = Field(default=StudyStatus.RASCUNHO.value)

    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default=None)


class EstudoCapitulo(SQLModel, table=True):
    """Divisao propria do ESTUDO — nao e o capitulo da obra.

    A ordem e unica dentro do estudo e define a progressao do aluno (que so
    acontece quando a liberacao por capitulo existir, em DEM futura).
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    estudo_id: int = Field(foreign_key="estudo.id", index=True)
    ordem: int
    titulo: str = Field(default="")
    conteudo_md: str = Field(default="")
    # Copiado como texto opaco: nao e parseado nem revalidado nesta DEM.
    questions_json: str = Field(default="[]")
    status: str = Field(default=StudyStatus.RASCUNHO.value)

    created_at: Optional[datetime] = Field(default=None)


class EstudoCapituloOrigem(SQLModel, table=True):
    """Mapa de origem: de qual capitulo da obra (e adendo) veio este do estudo.

    N:N por desenho. `adendo_id` e, nesta DEM, apenas referencia exibida na tela —
    o uso do adendo no fluxo de avaliacao e da Acao 1.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    estudo_capitulo_id: int = Field(foreign_key="estudocapitulo.id", index=True)
    obra_capitulo_id: int = Field(foreign_key="obracapitulo.id", index=True)
    adendo_id: Optional[int] = Field(default=None, foreign_key="adendo.id")

    created_at: Optional[datetime] = Field(default=None)
