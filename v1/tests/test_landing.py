import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from v1.landing import create_app

RAIZ = Path(__file__).resolve().parents[2]
YAML_PREENCHIDO = """
depoimentos:
  - nome: Ana
    texto: O estudo me sustentou.
    cidade: Recife
    estado: PE
    profissao_fe: Presbiteriana
    ativo: true
    ordem: 2
  - nome: Inativo
    texto: Este depoimento nao deve aparecer.
    ativo: false
    ordem: 1
contato:
  email: contato@didasko.app.br
  whatsapp: 55 11 99999-0000
hero:
  titulo: Titulo sobreposto
  subtitulo: Sub sobreposto
sobre:
  texto: Texto sobreposto do sobre.
homenagens:
  - titulo: Quem ensinou
    descricao: Um legado de ensino.
    referencia: o primeiro instrutor
"""
BASTIDOR = ("n+1", "snapshot", "padrão visual desta casa", "hash do", "versão n+1")


@pytest.fixture
def vazio(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    app = create_app(login_url="/login")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def preenchido(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    caminho = tmp_path / "landing.yaml"
    caminho.write_text(YAML_PREENCHIDO, encoding="utf-8")
    app = create_app(conteudo_path=caminho, login_url="/login")
    with TestClient(app) as client:
        yield client


def test_landing_sobe_sem_database_url_nem_session_secret(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    assert "DATABASE_URL" not in os.environ
    app = create_app(login_url="/login")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200


def test_landing_recusa_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///didasko_v1.db")
    with pytest.raises(RuntimeError, match="nao recebe DATABASE_URL"):
        create_app(login_url="/login")


def test_rf_landing_raiz_200_secoes_lang_alt(vazio):
    r = vazio.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'lang="pt-BR"' in html
    assert "<title>Didasko — Estudos Bíblicos Dirigidos</title>" in html
    assert 'alt="Logotipo do Didasko:' in html
    assert 'id="didasko"' in html
    assert 'id="obras"' in html
    assert 'id="quem"' in html
    assert 'id="niveis"' in html
    assert 'id="homenagens"' in html
    assert 'id="contato"' in html
    assert "Administrador" in html and "Revisor" in html and "Coordenador" in html
    assert "Instrutor" in html and "Aluno" in html
    assert "fetchpriority=\"high\"" in html


def test_rf_landing_homenagens_200(vazio):
    r = vazio.get("/homenagens")
    assert r.status_code == 200
    html = r.text
    assert 'lang="pt-BR"' in html
    assert "Homenagens — Didasko" in html
    assert "Gente que serviu" in html
    assert "O homenageado" not in html
    assert "A homenageada" not in html


def test_rf_landing_yaml_vazio_sem_depoimentos_sem_canais_sem_em_breve(vazio):
    html = vazio.get("/").text
    hom = vazio.get("/homenagens").text
    assert 'id="depoimentos"' not in html
    assert "Em breve" not in html
    assert "mailto:" not in html and "mailto:" not in hom
    assert "wa.me" not in html and "wa.me" not in hom
    assert "contato@gsi-ebd.com.br" not in html
    assert "5500000000000" not in html
    assert "Quero participar" in html
    assert "Os canais de contato aparecem quando estiverem cadastrados." in html


def test_rf_landing_yaml_preenchido_renderiza_ativos_e_canais(preenchido):
    html = preenchido.get("/").text
    hom = preenchido.get("/homenagens").text
    assert 'id="depoimentos"' in html
    assert "O estudo me sustentou." in html
    assert "Ana" in html
    assert "Recife" in html
    assert "Inativo" not in html
    assert "Este depoimento nao deve aparecer." not in html
    assert "Em breve" not in html
    assert 'href="mailto:contato@didasko.app.br"' in html
    assert 'href="https://wa.me/5511999990000"' in html
    assert "Os canais de contato aparecem quando estiverem cadastrados." not in html
    assert "Titulo sobreposto" in html
    assert "Sub sobreposto" in html
    assert "Texto sobreposto do sobre." in html
    assert "Quem ensinou" in hom
    assert "Um legado de ensino." in hom
    assert "o primeiro instrutor" in hom


def test_rf_landing_obras_tem_as_duas_definicoes(vazio):
    html = vazio.get("/").text
    assert "<h3>A obra</h3>" in html
    assert "É a fonte:" in html
    assert "<h3>O estudo dirigido</h3>" in html
    assert "É a obra aplicada:" in html


def test_rf_landing_sem_linguagem_de_bastidor(vazio, preenchido):
    for pagina in (vazio.get("/").text, vazio.get("/homenagens").text,
                   preenchido.get("/").text, preenchido.get("/homenagens").text):
        baixo = pagina.lower()
        for termo in BASTIDOR:
            assert termo not in baixo, termo
        assert "em breve" not in baixo


def test_rf_landing_sem_js_de_terceiros(vazio):
    html = vazio.get("/").text.lower()
    hom = vazio.get("/homenagens").text.lower()
    css = (RAIZ / "v1" / "static" / "landing" / "landing.css").read_text(encoding="utf-8").lower()
    for blob in (html, hom, css):
        assert "<script" not in blob
        assert "cdn." not in blob
        assert "googleapis" not in blob
        assert "gtag" not in blob
        assert "analytics" not in blob


def test_rf_landing_orcamento_carga_inicial(vazio):
    html = vazio.get("/").content
    pasta = RAIZ / "v1" / "static" / "landing"
    css = (pasta / "landing.css").stat().st_size
    topo = (pasta / "logo-88.webp").stat().st_size
    hero = (pasta / "logo-440.webp").stat().st_size
    hero2x = (pasta / "logo-880.webp").stat().st_size
    inicial = len(html) + css + topo + hero
    assert inicial < 500 * 1024, inicial
    assert inicial + hero2x < 500 * 1024, inicial + hero2x


def test_rf_landing_menu_hamburguer_abaixo_de_1000px():
    css = (RAIZ / "v1" / "static" / "landing" / "landing.css").read_text(encoding="utf-8")
    assert "@media (max-width: 1000px)" in css
    assert ".menu__alternador:checked ~ .menu" in css
    assert ".menu .botao--primario { color: #fff; }" in css
    assert ".menu .botao--contorno { color: var(--roxo); }" in css


def test_rf_landing_modulo_nao_importa_banco():
    for nome in ("landing.py", "landing_conteudo.py"):
        texto = (RAIZ / "v1" / nome).read_text(encoding="utf-8")
        assert "v1.db" not in texto
        assert "v1.auth" not in texto
        assert "gsi_ebd" not in texto
        assert "sqlmodel" not in texto.lower()
        assert "sqlalchemy" not in texto.lower()


def test_rf_landing_yaml_commitado_esta_vazio():
    texto = (RAIZ / "v1" / "landing.yaml").read_text(encoding="utf-8")
    assert "depoimentos: []" in texto
    assert "contato: {}" in texto
    assert "homenagens: []" in texto
    assert "mailto:" not in texto
    assert "wa.me" not in texto
    assert "contato@gsi-ebd.com.br" not in texto
