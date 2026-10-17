"""Compila TODAS as páginas — o teste que faltava.

Por que este arquivo existe: em 16/10 um `var + " texto"` dentro de um
`rx.foreach` derrubou o app em **loop de restart** em produção. O Reflex compila a
página quando a função dela é CHAMADA — então importar o módulo passa, importar o
app passa, e o erro só aparece no build/start:

    TypeError: unsupported operand type(s) for +: 'ObjectItemOperation' and 'str'

Chamar cada `*_page()` aqui reproduz exatamente esse passo da compilação, em
segundos e antes do deploy.
"""
import pytest

PAGINAS = (
    ("landing", "gsi_ebd.landing_content.controller", "landing_page_full"),
    ("login", "gsi_ebd.pages.login", "login_page"),
    ("admin", "gsi_ebd.pages.admin", "admin_page"),
    ("aluno", "gsi_ebd.pages.aluno", "aluno_page"),
    ("lesson", "gsi_ebd.pages.lesson", "lesson_page"),
    ("coordenador", "gsi_ebd.pages.coordenador", "coordenador_page"),
    ("revisao", "gsi_ebd.pages.revisao", "revisao_page"),
    ("pareceres", "gsi_ebd.pages.pareceres", "pareceres_page"),
    ("homenagens", "gsi_ebd.pages.homenagens", "homenagens_page"),
)


@pytest.mark.parametrize("nome,modulo,funcao", PAGINAS, ids=[p[0] for p in PAGINAS])
def test_pagina_compila(nome: str, modulo: str, funcao: str):
    """Chamar a função da página é o mesmo passo que falhou em produção."""
    import importlib

    mod = importlib.import_module(modulo)
    componente = getattr(mod, funcao)
    componente()
