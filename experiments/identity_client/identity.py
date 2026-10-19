from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Identity:
    subject: str
    role: str
    environment: str


class IdentityProvider(Protocol):
    def from_verified_claims(self, claims: dict) -> Identity: ...


class IdentityDenied(ValueError):
    pass


@dataclass(frozen=True)
class TokenIdentityProvider:
    organization_id: str
    environment: str
    project_id: str
    organization_claim: str
    roles_claim: str

    def from_verified_claims(self, claims: dict) -> Identity:
        org = claims.get(self.organization_claim)
        if org != self.organization_id or not claims.get("sub"):
            raise IdentityDenied("Identidade fora do ambiente permitido")
        roles = claims.get(self.roles_claim, {})
        groups = roles if isinstance(roles, list) else [roles]
        for external, internal in (("coordenador", "coordenador"), ("instrutor", "instrutor")):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                grants = group.get(external, {})
                if isinstance(grants, dict) and self.organization_id in grants:
                    return Identity(str(claims["sub"]), internal, self.environment)
        raise IdentityDenied("Papel ausente ou de outra organizacao")
