"""Decisoes do inventario carregadas uma vez por caminho configurado."""
import csv
import os
from functools import lru_cache
from pathlib import Path


class FonteInvalida(ValueError):
    pass


def caminho_inventario() -> Path:
    configurado = os.environ.get("CAMINHO_INVENTARIO")
    if configurado:
        return Path(configurado).resolve()
    return Path(__file__).resolve().parents[4] / "documentacao/fontes/inventario.csv"


@lru_cache(maxsize=None)
def _carregar(caminho: Path) -> dict[str, str]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        if not {"id", "decisao"}.issubset(leitor.fieldnames or []):
            raise FonteInvalida("Inventario sem id ou decisao")
        fontes = {}
        for linha in leitor:
            fonte_id = linha["id"].strip()
            decisao = linha["decisao"].strip()
            if not fonte_id or fonte_id in fontes:
                raise FonteInvalida("Identificador ausente ou duplicado")
            if decisao not in {"entra", "depende", "nao_entra"}:
                raise FonteInvalida("Decisao desconhecida no inventario")
            fontes[fonte_id] = decisao
        return fontes


def fonte_decisao(fonte_id: str) -> str:
    fontes = _carregar(caminho_inventario())
    try:
        return fontes[fonte_id]
    except KeyError as erro:
        raise FonteInvalida("Fonte ausente do inventario") from erro
