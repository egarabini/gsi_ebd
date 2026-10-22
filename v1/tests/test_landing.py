import os
import shutil
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from v1.landing import create_app
from v1.landing_assets import HASH_NOME, hash_conteudo, nome_versionado

RAIZ = Path(__file__).resolve().parents[2]
CACHE_IMUTAVEL = "public, max-age=31536000, immutable"
CACHE_REVALIDA = "no-cache"
LOGO_88 = RAIZ / "v1/static/landing/logo-88.webp"

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


class _Elementos(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elementos = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))


def _url_logo(dados: bytes) -> str:
    return "/static/landing/" + nome_versionado("logo-88.webp", dados)


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


@pytest.mark.parametrize("rota", ["/", "/homenagens"])
def test_rf_landing_logo_recortado_topo_45_rodape_34(vazio, rota):
    resposta = vazio.get(rota)
    elementos = _Elementos(resposta.text).elementos
    imagens = [attrs for tag, attrs in elementos if tag == "img"]
    topo = next(attrs for attrs in imagens if attrs.get("class") == "marca__logo")
    rodape = next(attrs for attrs in imagens if attrs.get("sizes") == "34px")
    imagem = LOGO_88.read_bytes()
    url = _url_logo(imagem)
    assert HASH_NOME.match(url.rsplit("/", 1)[1])
    for attrs, tamanho in ((topo, "45"), (rodape, "34")):
        assert attrs["src"] == url
        assert attrs["srcset"] == f"{url} 90w"
        assert attrs["sizes"] == f"{tamanho}px"
        assert attrs["width"] == attrs["height"] == tamanho
    css_url = next(attrs["href"] for tag, attrs in elementos if tag == "link")
    css = vazio.get(css_url)
    assert css.status_code == 200
    assert ".marca__logo { width: 45px; height: 45px;" in css.text
    assert len(imagem) == 7866


@pytest.mark.parametrize("rota", ["/", "/homenagens"])
def test_rf_landing_cache_html_etag_assets_imutaveis(vazio, rota):
    resposta = vazio.get(rota)
    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == CACHE_REVALIDA
    assert resposta.headers["etag"]
    revalidado = vazio.get(rota, headers={"If-None-Match": resposta.headers["etag"]})
    assert revalidado.status_code == 304
    assert revalidado.headers["cache-control"] == CACHE_REVALIDA
    assert revalidado.headers["etag"] == resposta.headers["etag"]
    elementos = _Elementos(resposta.text).elementos
    css_url = next(attrs["href"] for tag, attrs in elementos if tag == "link")
    assert HASH_NOME.match(css_url.rsplit("/", 1)[1])
    css = vazio.get(css_url)
    assert css.status_code == 200
    assert css.headers["cache-control"] == CACHE_IMUTAVEL
    urls = {attrs["src"] for tag, attrs in elementos if tag == "img"}
    urls.update(
        parte.strip().split()[0]
        for attrs in (a for t, a in elementos if t == "img")
        for parte in (attrs.get("srcset") or "").split(",")
        if parte.strip()
    )
    for url in urls:
        nome = url.rsplit("/", 1)[1]
        assert HASH_NOME.match(nome), url
        imagem = vazio.get(url)
        assert imagem.status_code == 200
        assert imagem.headers["cache-control"] == CACHE_IMUTAVEL
        digest = hash_conteudo(imagem.content)
        assert nome.split(".")[-2] == digest
    assert vazio.get("/static/landing/logo-88.webp").status_code == 404
    assert vazio.get("/static/landing/logo-88." + ("0" * 16) + ".webp").status_code == 404


def test_rf_landing_url_muda_quando_conteudo_muda(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    origem = RAIZ / "v1/static/landing"
    pasta = tmp_path / "static"
    pasta.mkdir()
    for arquivo in origem.iterdir():
        if arquivo.is_file():
            shutil.copy2(arquivo, pasta / arquivo.name)
    logo = pasta / "logo-88.webp"
    url_antes = _url_logo(logo.read_bytes())
    with TestClient(create_app(login_url="/login", static_dir=pasta)) as client:
        html = client.get("/").text
        assert url_antes in html
        assert f"{url_antes} 90w" in html
    logo.write_bytes(logo.read_bytes() + b"\x00")
    url_depois = _url_logo(logo.read_bytes())
    assert url_antes != url_depois
    with TestClient(create_app(login_url="/login", static_dir=pasta)) as client:
        html = client.get("/").text
        assert url_depois in html
        assert f"{url_depois} 90w" in html
        assert url_antes not in html
        assert client.get(url_depois).status_code == 200
        assert client.get(url_antes).status_code == 404


def test_rf_landing_nome_versionado_deriva_do_conteudo():
    um = nome_versionado("logo-88.webp", b"aaa")
    outro = nome_versionado("logo-88.webp", b"bbb")
    assert um != outro
    assert um.startswith("logo-88.") and um.endswith(".webp")
    assert HASH_NOME.match(um) and HASH_NOME.match(outro)
    assert hash_conteudo(b"aaa") in um


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
    for nome in ("landing.py", "landing_conteudo.py", "landing_assets.py"):
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
