"""Referências cruzadas do OpenBible — dado de terceiros (CC-BY 4.0).

Carregado uma vez por `gsi_ebd/scripts/importar_referencias_cruzadas.py`, a partir
do TSV versionado em `DADOS_EXTERNOS/openbible/`.

Procedência, licença e formato: `DADOS_EXTERNOS/openbible/README.md`
Avaliação de viabilidade e curadoria: `Diagnostico/referencias-cruzadas.md`
"""
from typing import Optional

from sqlmodel import Field, SQLModel


class ReferenciaCruzada(SQLModel, table=True):
    """Um par "de → para" com a votação da comunidade.

    - `de_versiculo` é o código OSIS no formato `Livro.cap.vers` (`'John.3.16'`),
      o mesmo vocabulário do mapa canônico em `utils/livros.py` (campo `osis`).
      Nunca é intervalo: conferido no arquivo, 0 de 344.799 pares.
    - `para_versiculo` **pode** ser intervalo (`'Rom.8.5-Rom.8.8'`) — 25,6% dos
      pares são.
    - `votos` é o saldo da votação da comunidade: pode ser **negativo**
      (mínimo −86, mediana 3, máximo 1296). Negativo significa relação rejeitada,
      então quem consome precisa de um piso — ver o serviço de curadoria.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    de_versiculo: str = Field(index=True)
    para_versiculo: str
    votos: int = Field(default=0)
