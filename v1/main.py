"""App FastAPI da v1. A v0 (Reflex) nao e importada aqui."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import StrictUndefined
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from v1.auth import Sessoes
from v1.db import criar_engine, iniciar_banco
from v1.routers import login, raiz
from v1.views import render

RAIZ = Path(__file__).resolve().parent


def _segredo(valor: str | None) -> str:
    segredo = valor if valor is not None else os.environ.get("SESSION_SECRET", "")
    if len(segredo) < 32:
        raise RuntimeError("SESSION_SECRET precisa de 32 caracteres ou mais")
    return segredo


def _cookie_seguro(secure: bool | None) -> bool:
    if secure is not None:
        return secure
    return os.environ.get("COOKIE_SECURE", "1") not in {"0", "false", "False"}


def create_app(engine=None, secret_key: str | None = None, secure: bool | None = None) -> FastAPI:
    eng = engine or criar_engine(os.environ["DATABASE_URL"])
    iniciar_banco(eng)

    @asynccontextmanager
    async def vida(app: FastAPI):
        iniciar_banco(app.state.engine)
        yield

    app = FastAPI(lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = eng
    app.state.sessoes = Sessoes()
    templates = Jinja2Templates(directory=str(RAIZ / "templates"))
    templates.env.undefined = StrictUndefined
    app.state.templates = templates
    app.mount("/static", StaticFiles(directory=str(RAIZ / "static")), name="static")
    app.include_router(login.router)
    app.include_router(raiz.router)

    @app.exception_handler(HTTPException)
    async def http_erro(request: Request, exc: HTTPException):
        try:
            return render(
                request,
                "erro.html",
                {"status": exc.status_code, "detalhe": str(exc.detail)},
                status_code=exc.status_code,
            )
        except Exception:
            return HTMLResponse(str(exc.detail), status_code=exc.status_code)

    app.add_middleware(
        SessionMiddleware,
        secret_key=_segredo(secret_key),
        session_cookie="didasko_v1",
        max_age=3600,
        same_site="lax",
        https_only=_cookie_seguro(secure),
    )
    return app
