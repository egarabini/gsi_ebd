import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from v1.auth import Sessoes, verificar_csrf, verificar_h14
from v1.db import criar_engine, iniciar_banco


def create_app(database_url=None, secret_key=None, engine=None, secure=None):
    segredo = secret_key or os.environ.get("SESSION_SECRET", "")
    if len(segredo) < 32:
        raise RuntimeError("Configure SESSION_SECRET com pelo menos 32 caracteres aleatorios")
    banco = engine if engine is not None else criar_engine(database_url)
    @asynccontextmanager
    async def lifespan(app):
        iniciar_banco(banco)
        yield
        if engine is None:
            banco.dispose()
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None,
                  dependencies=[Depends(verificar_h14), Depends(verificar_csrf)])
    app.state.engine = banco
    app.state.sessoes = Sessoes()
    raiz = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(raiz / "templates"),
                      autoescape=select_autoescape(), undefined=StrictUndefined)
    app.state.templates = Jinja2Templates(env=env)
    cookie_seguro = os.environ.get("COOKIE_SECURE", "true").lower() == "true" if secure is None else secure
    app.add_middleware(SessionMiddleware, secret_key=segredo, session_cookie="didasko_v1",
                       max_age=3600, same_site="lax", https_only=cookie_seguro)
    app.mount("/static", StaticFiles(directory=raiz / "static"), name="static")
    from v1.routers import login, admin_obras, revisor_obras, obra_detalhe
    for router in (login.router, admin_obras.router, revisor_obras.router, obra_detalhe.router):
        app.include_router(router)
    @app.exception_handler(HTTPException)
    async def erro_http(request: Request, exc):
        from v1.views import render
        return render(request, "erro.html", titulo="Acesso ou acao recusada", erro=str(exc.detail), status=exc.status_code)
    return app
