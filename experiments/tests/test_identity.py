import base64
import hashlib
import json
import time
from dataclasses import asdict, replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey

from experiments.identity_client.app import create_app
from experiments.identity_client.config import Settings
from experiments.identity_client.identity import IdentityDenied, TokenIdentityProvider


@pytest.fixture
def settings():
    return Settings(issuer="https://identity.test", public_url="https://app.test/experimento",
                    client_id="client", client_secret="test-only-client", session_secret="s" * 40,
                    organization_id="org", project_id="project", environment="ambiente-1",
                    scopes="roles", organization_claim="organization", roles_claim="roles",
                    provisioning_org_header="x-org", provisioning_token="test-only-service")


class Server:
    def __init__(self, settings):
        self.cfg = settings
        self.key = RSAKey.generate_key(2048, parameters={"kid": "key"})
        self.nonce = None
        self.claim_changes = {}
        self.signature_key = None
        self.calls = []
        self.grant_status = 200

    def handle(self, request):
        self.calls.append(request)
        issuer = self.cfg.issuer
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(200, json={"issuer": issuer, "authorization_endpoint": issuer + "/authorize",
                "token_endpoint": issuer + "/token", "jwks_uri": issuer + "/keys",
                "id_token_signing_alg_values_supported": ["RS256"]})
        if request.url.path == "/keys":
            return httpx.Response(200, json={"keys": [self.key.as_dict(private=False)]})
        if request.url.path == "/token":
            now = int(time.time())
            claims = {"iss": issuer, "aud": "client", "sub": "user", "iat": now, "exp": now + 300,
                      "nonce": self.nonce, "organization": "org", "roles": {"coordenador": {"org": "domain"}}}
            claims.update(self.claim_changes)
            token = jwt.encode({"alg": "RS256", "kid": "key"}, claims, self.signature_key or self.key)
            return httpx.Response(200, json={"access_token": "opaque", "token_type": "Bearer", "id_token": token})
        if request.url.path == "/v2/users/new":
            return httpx.Response(200, json={"id": "instructor"})
        if request.url.path.endswith("/grants"):
            return httpx.Response(self.grant_status, json={"userGrantId": "grant"})
        raise AssertionError(request.url)


@pytest.fixture
def browser(settings):
    server = Server(settings)
    app = create_app(settings, transport=httpx.MockTransport(server.handle))
    with TestClient(app, base_url="https://app.test/experimento", follow_redirects=False) as client:
        yield client, server


def start(client, server):
    response = client.get("login")
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    server.nonce = query["nonce"][0]
    return query


def enter(client, server):
    query = start(client, server)
    response = client.get("callback", params={"code": "code", "state": query["state"][0]})
    return response, query


def test_e01_real_authlib_mocked_oidc_pkce_role_environment(browser):
    client, server = browser
    response, query = enter(client, server)
    assert response.status_code == 303
    assert query["code_challenge_method"] == ["S256"]
    assert query["prompt"] == ["login"]
    post = next(r for r in server.calls if r.url.path == "/token")
    verifier = parse_qs(post.content.decode())["code_verifier"][0]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert query["code_challenge"] == [challenge]
    assert query["redirect_uri"] == ["https://app.test/experimento/callback"]
    me = client.get("me").json()
    assert (me["subject"], me["role"], me["environment"]) == ("user", "coordenador", "ambiente-1")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "id_token" not in cookie and "opaque" not in cookie
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("changes", [{"iss": "https://evil.test"}, {"aud": "other"},
    {"exp": 1}, {"nonce": "wrong"}, {"organization": "other"}, {"roles": {}},
    {"roles": {"coordenador": {"other": "domain"}}}])
def test_e01_invalid_token_denied(browser, changes):
    client, server = browser
    server.claim_changes = changes
    response, _ = enter(client, server)
    assert response.status_code == 401
    assert client.get("me").status_code == 401


def test_e01_signature_denied(browser):
    client, server = browser
    server.signature_key = RSAKey.generate_key(2048, parameters={"kid": "key"})
    assert enter(client, server)[0].status_code == 401


def test_e01_state_and_replay_denied(browser):
    client, server = browser
    query = start(client, server)
    assert client.get("callback", params={"code": "x", "state": "bad"}).status_code == 401
    response, query = enter(client, server)
    assert response.status_code == 303
    assert client.get("callback", params={"code": "code", "state": query["state"][0]}).status_code == 401


def test_e02_e03_provisioning_and_local_logout(browser):
    client, server = browser
    enter(client, server)
    csrf = client.get("me").json()["csrf_token"]
    data = {"email": "instructor@example.test", "first_name": "Teste", "last_name": "Local", "initial_password": "Test-only-123!"}
    headers = {"x-csrf-token": csrf, "origin": "https://app.test"}
    result = client.post("instructors", json=data, headers=headers)
    assert result.status_code == 201
    assert result.json()["role"] == "instrutor"
    create = next(r for r in server.calls if r.url.path == "/v2/users/new")
    body = json.loads(create.content)
    assert body["organizationId"] == "org"
    assert body["human"]["password"]["changeRequired"] is True
    assert create.headers["x-org"] == "org"
    grant = next(r for r in server.calls if r.url.path.endswith("/grants"))
    assert json.loads(grant.content) == {"projectId": "project", "roleKeys": ["instrutor"]}
    assert "Test-only" not in result.text
    assert client.post("logout", headers=headers).status_code == 200
    assert client.get("me").status_code == 401


@pytest.mark.parametrize("path", ["logout", "instructors"])
@pytest.mark.parametrize("bad", ["missing", "token", "origin"])
def test_csrf_denies(browser, path, bad):
    client, server = browser
    enter(client, server)
    csrf = client.get("me").json()["csrf_token"]
    headers = {"x-csrf-token": csrf, "origin": "https://app.test"}
    if bad == "missing": headers = {}
    elif bad == "token": headers["x-csrf-token"] = "wrong"
    else: headers["origin"] = "https://identity.test"
    data = {"email": "instructor@example.test", "first_name": "A", "last_name": "B", "initial_password": "abc"}
    assert client.post(path, headers=headers, json=data).status_code == 403


def test_e02_instructor_cannot_provision(browser):
    client, server = browser
    server.claim_changes = {"roles": {"instrutor": {"org": "domain"}}}
    enter(client, server)
    csrf = client.get("me").json()["csrf_token"]
    response = client.post("instructors", headers={"origin": "https://app.test", "x-csrf-token": csrf},
        json={"email": "a@b.test", "first_name": "A", "last_name": "B", "initial_password": "abc"})
    assert response.status_code == 403
    assert not any(r.url.path == "/v2/users/new" for r in server.calls)


def test_e02_partial_provision_visible_without_secret(browser):
    client, server = browser
    enter(client, server); server.grant_status = 500
    csrf = client.get("me").json()["csrf_token"]
    response = client.post("instructors", headers={"origin": "https://app.test", "x-csrf-token": csrf},
        json={"email": "a@b.test", "first_name": "A", "last_name": "B", "initial_password": "never-return"})
    assert response.status_code == 502 and "never-return" not in response.text


@pytest.mark.parametrize("field,value", [("issuer", "http://identity.test"), ("issuer", "https:///"),
    ("public_url", "https://app.test/wrong"), ("session_secret", "short"), ("client_id", ""),
    ("issuer", "https://user:password@identity.test"), ("public_url", "https://app.test/experimento?x=1")])
def test_e07_invalid_configuration(settings, field, value):
    with pytest.raises(ValueError): replace(settings, **{field: value})


def test_e07_all_config_from_env(settings, monkeypatch):
    for name, value in asdict(settings).items(): monkeypatch.setenv(name.upper(), value)
    assert Settings.from_env() == settings
    assert "test-only" not in repr(settings)


def test_e07_interface_replaceable(settings):
    from experiments.identity_client.identity import Identity
    class Alternate:
        def from_verified_claims(self, claims): return Identity("alternate", "instrutor", "other")
    server = Server(settings)
    with TestClient(create_app(settings, Alternate(), httpx.MockTransport(server.handle)),
                    base_url="https://app.test/experimento", follow_redirects=False) as client:
        assert enter(client, server)[0].status_code == 303
        assert client.get("me").json()["subject"] == "alternate"


def test_e07_routes_and_code_paths_neutral(settings):
    app = create_app(settings)
    assert {r.path for r in app.routes} == {"/health", "/login", "/callback", "/me", "/logout", "/instructors"}
    assert app.root_path == "/experimento"
    code = Path("experiments/identity_client")
    assert not any("zitadel" in str(p).lower() or "zitadel" in p.read_text().lower() for p in code.glob("*.py"))
    example = Path("experiments/zitadel/.env.example").read_text().splitlines()
    assert example and all(line.endswith("=") and line.count("=") == 1 for line in example)


def test_infra_config_isolated():
    compose = yaml.safe_load(Path("experiments/zitadel/docker-compose.yml").read_text())
    assert compose["name"] == "experimento-oidc"
    assert compose["networks"]["edge"] == {"external": True, "name": "deploy_didasko"}
    services = compose["services"]
    assert [v["mem_limit"] for v in services.values()] == ["512m", "256m", "128m"]
    assert not any("ports" in v for v in services.values())
    assert services["identity-api"]["labels"]["traefik.http.services.identity-api.loadbalancer.server.scheme"] == "h2c"
    assert services["identity-api"]["image"].endswith(":v4.19.5")
    assert services["identity-login"]["image"].endswith(":v4.19.5")
    assert "didasko:" not in json.dumps(compose)
