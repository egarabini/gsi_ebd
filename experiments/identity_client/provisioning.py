import httpx


class ProvisioningError(Exception):
    pass


class ProvisioningClient:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport

    async def create_instructor(self, data):
        cfg = self.settings
        headers = {"Authorization": "Bearer " + cfg.provisioning_token,
                   cfg.provisioning_org_header: cfg.organization_id}
        body = {"organizationId": cfg.organization_id, "username": data.email,
                "human": {"profile": {"givenName": data.first_name, "familyName": data.last_name},
                          "email": {"email": data.email, "isVerified": True},
                          "password": {"password": data.initial_password.get_secret_value(),
                                       "changeRequired": True}}}
        async with httpx.AsyncClient(transport=self.transport, timeout=15) as api:
            try:
                response = await api.post(cfg.issuer + "/v2/users/new", headers=headers, json=body)
                response.raise_for_status()
                uid = response.json()["id"]
                grant = await api.post(cfg.issuer + f"/management/v1/users/{uid}/grants",
                                       headers=headers, json={"projectId": cfg.project_id,
                                                             "roleKeys": ["instrutor"]})
                grant.raise_for_status()
                return uid
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                # Nao apagar usuario parcial: preservar evidencia sem expor a credencial.
                raise ProvisioningError("Provisao incompleta") from exc
