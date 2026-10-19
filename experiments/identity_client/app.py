import hmac
from dataclasses import asdict
from secrets import token_urlsafe
from time import monotonic

import httpx
from joserfc.errors import JoseError
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, SecretStr
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings
from .identity import IdentityDenied, IdentityProvider, TokenIdentityProvider


class InstructorInput(BaseModel):
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    initial_password: SecretStr


def create_app(settings: Settings, identity_provider: IdentityProvider | None = None,
               transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    app = FastAPI(root_path="/experimento", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret,
                       session_cookie="__Secure-didasko-experiment", path="/experimento",
                       https_only=True, same_site="lax", max_age=600)
    provider = identity_provider or TokenIdentityProvider(
        settings.organization_id, settings.environment, settings.project_id,
        settings.organization_claim, settings.roles_claim)
    sessions = {}
    oauth = OAuth()
    kwargs = {"scope": " ".join((
        "openid", "profile", *settings.scopes.split(),
    )), "code_challenge_method": "S256",
        "token_endpoint_auth_method": "client_secret_basic" if settings.client_secret else "none"}
    if transport is not None:
        kwargs["transport"] = transport
    client = oauth.register(
        "provider", client_id=settings.client_id, client_secret=settings.client_secret or None,
        server_metadata_url=settings.issuer + "/.well-known/openid-configuration",
        client_kwargs=kwargs,
    )

    def cleanup():
        for sid in list(sessions):
            if sessions[sid]["expires"] <= monotonic():
                del sessions[sid]

    def authenticated(request: Request):
        cleanup()
        session = sessions.get(request.session.get("sid"))
        if session is None:
            raise HTTPException(401, "Login necessario")
        return session

    def verify_csrf(request: Request, session):
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf"]):
            raise HTTPException(403, "CSRF invalido")
        if request.headers.get("origin") != settings.public_url.rsplit("/experimento", 1)[0]:
            raise HTTPException(403, "Origem invalida")

    @app.middleware("http")
    async def no_cache(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "experiment": "DEM-016"}

    @app.get("/login")
    async def login(request: Request):
        cleanup()
        old = request.session.get("sid")
        sessions.pop(old, None)
        request.session.clear()
        # Forca autenticacao nova para nao medir um redirect de SSO em E-05.
        return await client.authorize_redirect(
            request, settings.public_url + "/callback", prompt="login", max_age=0,
            code_verifier=token_urlsafe(48))

    @app.get("/callback")
    async def callback(request: Request):
        try:
            # Authlib verifica state, assinatura JWKS, issuer, audiencia, validade e nonce.
            token = await client.authorize_access_token(request, leeway=30, claims_options={"iss": {"essential": True, "values": [settings.issuer]}})
            claims = token.get("userinfo")
            if not token.get("id_token") or not claims:
                raise IdentityDenied("ID token obrigatorio")
            identity = provider.from_verified_claims(claims)
        except (OAuthError, JoseError, IdentityDenied, ValueError, httpx.HTTPError):
            request.session.clear()
            raise HTTPException(401, "Resposta OIDC recusada") from None
        request.session.clear()
        sid = token_urlsafe(32)
        sessions[sid] = {"identity": identity, "expires": monotonic() + 600,
                         "csrf": token_urlsafe(32)}
        # O cookie guarda somente um identificador; tokens nao vao ao navegador.
        request.session["sid"] = sid
        return RedirectResponse(settings.public_url + "/me", status_code=303)

    @app.get("/me")
    async def me(request: Request):
        session = authenticated(request)
        return {**asdict(session["identity"]), "csrf_token": session["csrf"]}

    @app.post("/logout")
    async def logout(request: Request):
        session = authenticated(request)
        verify_csrf(request, session)
        sessions.pop(request.session["sid"], None)
        request.session.clear()
        return {"status": "logged-out-locally"}

    @app.post("/instructors", status_code=201)
    async def provision(request: Request, data: InstructorInput):
        session = authenticated(request)
        verify_csrf(request, session)
        if session["identity"].role != "coordenador":
            raise HTTPException(403, "Somente coordenador")
        if not settings.provisioning_token:
            raise HTTPException(503, "Provisao nao configurada")
        from .provisioning import ProvisioningClient, ProvisioningError
        try:
            uid = await ProvisioningClient(settings, transport).create_instructor(data)
        except ProvisioningError:
            raise HTTPException(502, "Provisao incompleta; conferir usuario e grant no provedor") from None
        return {"subject": uid, "role": "instrutor", "environment": settings.environment}

    app.state.oidc_client = client
    return app
