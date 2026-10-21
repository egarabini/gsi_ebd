"""Le o v1/landing.yaml. Sem banco, sem rede, sem dado inventado."""
from pathlib import Path

import yaml

def _texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _whatsapp(valor) -> str:
    return "".join(ch for ch in _texto(valor) if ch.isdigit())


def _foto(valor) -> str:
    foto = _texto(valor)
    if not foto:
        return ""
    if foto.startswith("/") or foto.startswith("http://") or foto.startswith("https://"):
        return foto
    return "/static/landing/" + foto.lstrip("/")


def _depoimento(item) -> dict | None:
    if not isinstance(item, dict) or not item.get("ativo"):
        return None
    texto = _texto(item.get("texto"))
    if not texto:
        return None
    return {
        "nome": _texto(item.get("nome")),
        "texto": texto,
        "cidade": _texto(item.get("cidade")),
        "estado": _texto(item.get("estado")),
        "profissao_fe": _texto(item.get("profissao_fe")),
        "foto": _foto(item.get("foto")),
        "ordem": item.get("ordem") or 0,
    }


def _homenagem(item) -> dict | None:
    if not isinstance(item, dict):
        return None
    titulo = _texto(item.get("titulo") or item.get("nome"))
    if not titulo:
        return None
    return {
        "titulo": titulo,
        "descricao": _texto(item.get("descricao") or item.get("texto")),
        "referencia": _texto(item.get("referencia")),
    }


def carregar(caminho: Path | None = None) -> dict:
    arquivo = Path(caminho) if caminho else Path(__file__).resolve().parent / "landing.yaml"
    bruto = {}
    if arquivo.is_file():
        lido = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
        if isinstance(lido, dict):
            bruto = lido
    contato = bruto.get("contato") if isinstance(bruto.get("contato"), dict) else {}
    hero = bruto.get("hero") if isinstance(bruto.get("hero"), dict) else {}
    sobre = bruto.get("sobre") if isinstance(bruto.get("sobre"), dict) else {}
    depoimentos = [
        d for d in (_depoimento(item) for item in (bruto.get("depoimentos") or [])) if d
    ]
    depoimentos.sort(key=lambda item: item["ordem"])
    homenagens = [
        h for h in (_homenagem(item) for item in (bruto.get("homenagens") or [])) if h
    ]
    return {
        "depoimentos": depoimentos,
        "contato": {
            "email": _texto(contato.get("email")),
            "whatsapp": _whatsapp(contato.get("whatsapp")),
        },
        "hero": {
            "titulo": _texto(hero.get("titulo")),
            "subtitulo": _texto(hero.get("subtitulo")),
        },
        "sobre": {"texto": _texto(sobre.get("texto"))},
        "homenagens": homenagens,
    }
