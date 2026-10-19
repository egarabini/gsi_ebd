import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    issuer: str
    public_url: str
    client_id: str
    client_secret: str = field(repr=False)
    session_secret: str = field(repr=False)
    organization_id: str
    project_id: str
    environment: str
    scopes: str
    organization_claim: str
    roles_claim: str
    provisioning_org_header: str
    provisioning_token: str = field(default="", repr=False)

    def __post_init__(self):
        issuer = urlsplit(self.issuer)
        public = urlsplit(self.public_url)
        if issuer.scheme != "https" or not issuer.netloc or issuer.path not in ("", "/"):
            raise ValueError("Issuer deve ser uma origem HTTPS")
        if public.scheme != "https" or not public.netloc or public.path != "/experimento":
            raise ValueError("App deve usar HTTPS em /experimento")
        if not all((self.client_id, self.organization_id, self.project_id, self.environment, self.organization_claim, self.roles_claim, self.scopes, self.provisioning_org_header)):
            raise ValueError("IDs e ambiente sao obrigatorios")
        if len(self.session_secret) < 32:
            raise ValueError("SESSION_SECRET deve ter pelo menos 32 caracteres")
        for url in (issuer, public):
            if url.username or url.password or url.query or url.fragment:
                raise ValueError("URL invalida")

    @classmethod
    def from_env(cls):
        return cls(**{name: os.environ.get(name.upper(), "") for name in cls.__dataclass_fields__})
