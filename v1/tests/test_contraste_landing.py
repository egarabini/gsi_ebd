"""Contraste WCAG AA (4,5:1) do texto sobre o gradiente — o pior ponto.

A formula e a luminancia relativa (WCAG 2.1). Impede a regressao do ciano
atras do texto branco no .contato__cartao e no .botao--primario.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CSS = (RAIZ / "v1" / "static" / "landing" / "landing.css").read_text(encoding="utf-8")
LIMIAR = 4.5


def _sem_comentarios(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _bloco(css: str, seletor: str) -> str:
    padrao = re.compile(r"(?:^|})\s*" + re.escape(seletor) + r"\s*\{([^}]+)\}", re.S)
    achado = padrao.search(_sem_comentarios(css))
    assert achado, f"sem regra {seletor}"
    return achado.group(1)


def _decl(bloco: str, prop: str) -> str | None:
    for parte in bloco.split(";"):
        if ":" not in parte:
            continue
        chave, valor = parte.split(":", 1)
        if chave.strip() == prop:
            return valor.strip()
    return None


def _hex_rgb(valor: str) -> tuple[int, int, int]:
    h = valor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _variaveis(css: str) -> dict[str, str]:
    bloco = _bloco(css, ":root")
    encontrados = {}
    for parte in bloco.split(";"):
        if ":" not in parte:
            continue
        chave, valor = parte.split(":", 1)
        chave = chave.strip()
        if chave.startswith("--"):
            encontrados[chave] = valor.strip()
    return encontrados


def _resolve(token: str, variaveis: dict[str, str]) -> tuple[int, int, int]:
    token = token.strip()
    if token.startswith("var("):
        nome = token[4:-1].strip()
        return _resolve(variaveis[nome], variaveis)
    if token.startswith("#"):
        return _hex_rgb(token)
    raise AssertionError(f"cor nao reconhecida: {token}")


def _paradas(fundo: str, variaveis: dict[str, str]) -> list[tuple[int, int, int]]:
    if fundo.startswith("linear-gradient"):
        inner = fundo[fundo.find("(") + 1 : fundo.rfind(")")]
        cores = []
        for achado in re.finditer(r"#([0-9A-Fa-f]{3,8})|var\((--[a-z0-9-]+)\)", inner):
            if achado.group(1):
                cores.append(_hex_rgb("#" + achado.group(1)))
            else:
                cores.append(_resolve(f"var({achado.group(2)})", variaveis))
        assert cores, f"gradiente sem cores: {fundo}"
        return cores
    return [_resolve(fundo.split()[0], variaveis)]


def _amostras(paradas: list[tuple[int, int, int]], n: int = 21) -> list[tuple[int, int, int]]:
    if len(paradas) == 1:
        return paradas
    saida = []
    for i in range(n):
        t = i / (n - 1)
        seg = t * (len(paradas) - 1)
        j = min(int(seg), len(paradas) - 2)
        local = seg - j
        a, b = paradas[j], paradas[j + 1]
        saida.append(tuple(int(round(a[k] + (b[k] - a[k]) * local)) for k in range(3)))
    return saida


def _lin(canal: float) -> float:
    c = canal / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def razao(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, l2 = luminancia(c1), luminancia(c2)
    claro, escuro = max(l1, l2), min(l1, l2)
    return (claro + 0.05) / (escuro + 0.05)


def _mistura(fundo, frente, alfa: float):
    return tuple(int(round(fundo[k] * (1 - alfa) + frente[k] * alfa)) for k in range(3))


def pior_contraste(css: str, seletor: str, texto_seletor: str | None = None) -> float:
    variaveis = _variaveis(css)
    base = _bloco(css, seletor)
    fundo = _decl(base, "background") or _decl(base, "background-color")
    assert fundo, f"{seletor} sem background"
    cor = _decl(base, "color")
    alfa = 1.0
    if texto_seletor:
        texto = _bloco(css, texto_seletor)
        cor = _decl(texto, "color") or cor
        if _decl(texto, "opacity") is not None:
            alfa = float(_decl(texto, "opacity"))
    assert cor, f"{seletor} sem color"
    rgb_txt = _resolve(cor.split()[0], variaveis)
    pior = None
    for bg in _amostras(_paradas(fundo, variaveis)):
        visivel = _mistura(bg, rgb_txt, alfa)
        atual = razao(visivel, bg)
        if pior is None or atual < pior:
            pior = atual
    return pior


def test_rf_landing_contraste_contato_cartao_pior_ponto_aa():
    pior = pior_contraste(CSS, ".contato__cartao", ".contato__cartao p")
    assert pior >= LIMIAR, f".contato__cartao pior ponto {pior:.2f}:1 (limiar {LIMIAR})"


def test_rf_landing_contraste_botao_primario_pior_ponto_aa():
    pior = pior_contraste(CSS, ".botao--primario")
    assert pior >= LIMIAR, f".botao--primario pior ponto {pior:.2f}:1 (limiar {LIMIAR})"


def test_rf_landing_contraste_detecta_ciano_atras_do_texto():
    css = """
    :root { --roxo: #4B1E8C; --ciano: #29ABE2; }
    .contato__cartao { color: #fff; background: linear-gradient(125deg, #4B1E8C, #29ABE2); }
    .contato__cartao p { opacity: .92; }
    """
    pior = pior_contraste(css, ".contato__cartao", ".contato__cartao p")
    assert pior < LIMIAR, f"o ciano deveria reprovar, veio {pior:.2f}:1"
