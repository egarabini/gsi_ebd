"""RF07: leitura cacheada e validacao do inventario."""
from pathlib import Path

import pytest

from gsi_ebd.services import fontes


@pytest.fixture
def inventario(tmp_path, monkeypatch):
    caminho = tmp_path / "inventario.csv"
    caminho.write_text("id;decisao\nF-001;entra\nF-002;depende\nF-003;nao_entra\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(caminho))
    fontes._carregar.cache_clear()
    yield caminho
    fontes._carregar.cache_clear()


def test_rf07_le_csv_uma_vez_por_caminho(inventario, monkeypatch):
    original = Path.open
    chamadas = []

    def abrir(caminho, *args, **kwargs):
        chamadas.append(caminho)
        return original(caminho, *args, **kwargs)

    monkeypatch.setattr(Path, "open", abrir)
    assert fontes.fonte_decisao("F-001") == "entra"
    assert fontes.fonte_decisao("F-002") == "depende"
    assert fontes.fonte_decisao("F-003") == "nao_entra"
    assert chamadas == [inventario.resolve()]


def test_rf07_fonte_ausente_falha_fechado(inventario):
    with pytest.raises(fontes.FonteInvalida, match="ausente"):
        fontes.fonte_decisao("F-999")


@pytest.mark.parametrize("csv", ["nome;valor\na;b\n", "id;decisao\nF-001;talvez\n",
                                  "id;decisao\nF-001;entra\nF-001;depende\n"])
def test_rf07_inventario_invalido_bloqueia(inventario, csv):
    inventario.write_text(csv, encoding="utf-8")
    with pytest.raises(fontes.FonteInvalida):
        fontes.fonte_decisao("F-001")


def test_rf07_caminho_configuravel_isola_caches(inventario, tmp_path, monkeypatch):
    assert fontes.fonte_decisao("F-001") == "entra"
    outro = tmp_path / "outro.csv"
    outro.write_text("id;decisao\nF-001;depende\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(outro))
    assert fontes.fonte_decisao("F-001") == "depende"


def test_rf07_caminho_padrao_relativo_ao_projeto(monkeypatch):
    monkeypatch.delenv("CAMINHO_INVENTARIO", raising=False)
    assert fontes.caminho_inventario() == Path(fontes.__file__).resolve().parents[4] / "documentacao/fontes/inventario.csv"
