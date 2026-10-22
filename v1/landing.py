"""Landing publica da v1. Sem banco, sem sessao, sem login."""
import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from v1.landing_assets import (
    DESTINO as DESTINO_BUILD,
    HASH_NOME,
    ORIGEM as ORIGEM_PADRAO,
    urls_de_versionados,
    versionar,
)
from v1.landing_conteudo import carregar

RAIZ = Path(__file__).resolve().parent
CACHE_IMUTAVEL = "public, max-age=31536000, immutable"
CACHE_REVALIDA = "no-cache"


def create_app(conteudo_path=None, login_url=None, static_dir=None) -> FastAPI:
    # A landing nao recebe banco. O EVAL confere a ausencia da variavel no conteiner;
    # recusar aqui impede um compose mal montado de passar silenciosamente.
    if os.environ.get("DATABASE_URL"):
        raise RuntimeError("A landing nao recebe DATABASE_URL")
    dados = carregar(Path(conteudo_path) if conteudo_path else os.environ.get("LANDING_YAML"))
    entrar = login_url if login_url is not None else os.environ.get("LANDING_LOGIN_URL", "/login")
    origem = Path(static_dir) if static_dir else ORIGEM_PADRAO
    pasta_static, assets, tmpdir = _preparar_static(origem)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if tmpdir is not None:
            tmpdir.cleanup()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    env = Environment(
        loader=FileSystemLoader(RAIZ / "templates"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    env.globals["asset_url"] = lambda nome: assets[nome]

    @app.middleware("http")
    async def cache_landing(request: Request, call_next):
        response = await call_next(request)
        if response.status_code not in (200, 304):
            return response
        nome = request.url.path.rsplit("/", 1)[-1]
        # Cache longo so para a URL que identifica o conteudo no nome.
        if request.url.path.startswith("/static/landing/") and HASH_NOME.match(nome):
            response.headers["Cache-Control"] = CACHE_IMUTAVEL
        else:
            response.headers["Cache-Control"] = CACHE_REVALIDA
        return response

    app.state.templates = Jinja2Templates(env=env)
    app.state.landing = dados
    app.state.login_url = entrar
    app.state.assets_tmpdir = tmpdir
    app.mount("/static/landing", StaticFiles(directory=str(pasta_static)), name="landing")

    @app.get("/")
    def inicio(request: Request):
        return _pagina(request, "landing/index.html", "Didasko — Estudos Bíblicos Dirigidos")

    @app.get("/homenagens")
    def homenagens(request: Request):
        return _pagina(request, "landing/homenagens.html", "Homenagens — Didasko")

    return app


def _preparar_static(origem: Path):
    """Usa o dir gerado no build da imagem; senão versiona na hora (testes)."""
    if origem.resolve() == ORIGEM_PADRAO.resolve():
        pre = urls_de_versionados(DESTINO_BUILD)
        if pre:
            return DESTINO_BUILD, pre, None
    tmpdir = TemporaryDirectory(prefix="landing-assets-")
    urls = versionar(origem, Path(tmpdir.name))
    return Path(tmpdir.name), urls, tmpdir


def _pagina(request: Request, nome: str, titulo: str):
    dados = request.app.state.landing
    resposta = request.app.state.templates.TemplateResponse(
        request=request,
        name=nome,
        context={
            "titulo": titulo,
            "login_url": request.app.state.login_url,
            "hero": dados["hero"],
            "sobre": dados["sobre"],
            "contato": dados["contato"],
            "depoimentos": dados["depoimentos"],
            "homenagens": dados["homenagens"],
        },
    )
    etag = '"' + hashlib.sha256(resposta.body).hexdigest()[:16] + '"'
    resposta.headers["ETag"] = etag
    resposta.headers["Cache-Control"] = CACHE_REVALIDA
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": CACHE_REVALIDA})
    return resposta
