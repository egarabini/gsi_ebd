"""O seed de alunos fake recusa producao e qualquer banco que nao seja didasko_v1."""
from pathlib import Path

import pytest

from v1.db import assert_banco_v1
from v1.seed_homolog_estudo import recusar_producao


def test_seed_homolog_recusa_producao():
    with pytest.raises(RuntimeError, match="producao"):
        recusar_producao(
            url="postgresql+psycopg2://didasko_v1:segredo@postgres:5432/didasko_v1",
            ambiente="producao",
        )


def test_seed_homolog_recusa_banco_que_nao_e_didasko_v1():
    with pytest.raises(RuntimeError):
        recusar_producao(
            url="postgresql+psycopg2://didasko:segredo@postgres:5432/didasko",
            ambiente="homologacao",
        )
    with pytest.raises(RuntimeError):
        assert_banco_v1("postgresql+psycopg2://didasko:segredo@postgres:5432/didasko")


def test_seed_homolog_aceita_didasko_v1_de_homologacao():
    url = recusar_producao(
        url="postgresql+psycopg2://didasko_v1:segredo@postgres-v1:5432/didasko_v1",
        ambiente="homologacao",
    )
    assert url.endswith("/didasko_v1")


def test_seed_homolog_nao_vive_no_seed_de_producao():
    producao = (Path(__file__).resolve().parents[2] / "gsi_ebd" / "data" / "seed.py").read_text(
        encoding="utf-8"
    )
    homolog = (Path(__file__).resolve().parents[1] / "seed_homolog_estudo.py").read_text(encoding="utf-8")
    assert "aluno.fake.a@homolog.didasko.local" in homolog
    assert "aluno.fake.a@homolog.didasko.local" not in producao
    assert "seed_homolog_estudo" not in producao
