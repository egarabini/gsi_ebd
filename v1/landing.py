"""Landing publica da v1. Sem banco, sem sessao, sem login."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from starlette.templating import Jinja2Templates

from v1.landing_conteudo import carregar

RAIZ = Path(__file__).resolve().parent


def create_app(conteudo_path=None, login_url=None) -> FastAPI:
    # A landing nao recebe banco. O EVAL confere a ausencia da variavel no conteiner;
    # recusar aqui impede um compose mal montado de passar silenciosamente.
    if os.environ.get("DATABASE_URL"):
        raise RuntimeError("A landing nao recebe DATABASE_URL")
    dados = carregar(Path(conteudo_path) if conteudo_path else os.environ.get("LANDING_YAML"))
    entrar = login_url if login_url is not None else os.environ.get("LANDING_LOGIN_URL", "/login")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    env = Environment(
        loader=FileSystemLoader(RAIZ / "templates"),
        autoescape=select_autoescape(),
        undefined=StrictUndefined,
    )
    app.state.templates = Jinja2Templates(env=env)
    app.state.landing = dados
    app.state.login_url = entrar
    app.mount("/static/landing", StaticFiles(directory=str(RAIZ / "static" / "landing")), name="landing")

    @app.get("/")
    def inicio(request: Request):
        return _pagina(request, "landing/index.html", "Didasko — Estudos Bíblicos Dirigidos")

    @app.get("/homenagens")
    def homenagens(request: Request):
        return _pagina(request, "landing/homenagens.html", "Homenagens — Didasko")

    return app


def _pagina(request: Request, nome: str, titulo: str):
    dados = request.app.state.landing
    return request.app.state.templates.TemplateResponse(
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
