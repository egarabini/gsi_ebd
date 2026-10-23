"""Versiona os assets da landing: o hash do conteudo entra no nome.

O hash e gerado no build (a imagem Docker) e, nos testes, na subida do app.
Nunca e um numero de versao manual. Trocar o arquivo troca o nome — e a URL.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ORIGEM = RAIZ / "static" / "landing"
DESTINO = RAIZ / "static" / "landing-versionado"
HASH_NOME = re.compile(r"^(.+)\.([0-9a-f]{16})(\.[A-Za-z0-9]+)$")
DIGEST_LEN = 16


def hash_conteudo(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()[:DIGEST_LEN]


def nome_versionado(nome: str, dados: bytes) -> str:
    caminho = Path(nome)
    return f"{caminho.stem}.{hash_conteudo(dados)}{caminho.suffix}"


def versionar(origem: Path, destino: Path) -> dict[str, str]:
    """Copia cada arquivo para stem.<hash>.ext. Retorna {nome_origem: url}."""
    destino.mkdir(parents=True, exist_ok=True)
    for antigo in destino.iterdir():
        if antigo.is_file():
            antigo.unlink()
    urls: dict[str, str] = {}
    for path in sorted(origem.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        dados = path.read_bytes()
        hashed = nome_versionado(path.name, dados)
        shutil.copy2(path, destino / hashed)
        urls[path.name] = f"/static/landing/{hashed}"
    return urls


def urls_de_versionados(destino: Path) -> dict[str, str]:
    urls: dict[str, str] = {}
    if not destino.is_dir():
        return urls
    for path in destino.iterdir():
        achado = HASH_NOME.match(path.name)
        if not achado or not path.is_file():
            continue
        original = achado.group(1) + achado.group(3)
        urls[original] = f"/static/landing/{path.name}"
    return urls


if __name__ == "__main__":
    mapa = versionar(ORIGEM, DESTINO)
    for nome, url in mapa.items():
        print(f"{nome} -> {url}")
