"""Contrato do CI: o pull_request dispara em todo PR (opcao A, 23/10)."""
from pathlib import Path

import yaml

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def test_ci_pull_request_sem_filtro_de_branches():
    # PyYAML 1.1 le `on:` como True.
    dados = yaml.safe_load(CI.read_text(encoding="utf-8"))
    eventos = dados.get("on") or dados.get(True)
    disparo = eventos["pull_request"]
    assert disparo in (None, {}), disparo
    if isinstance(disparo, dict):
        assert "branches" not in disparo
    assert eventos["push"]["branches"] == ["develop", "main"]
    assert dados["jobs"]["testes"]["name"] == "testes (pytest)"
