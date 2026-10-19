import os
import secrets
from pathlib import Path


def main():
    expected = Path("/home/didasko-deploy/experimentos/didasko/experiments/zitadel")
    if os.name != "posix" or Path.cwd().resolve() != expected:
        raise SystemExit("Somente no diretorio autorizado da VPS, apos aprovacao d")
    destination = expected / ".env"
    values = dict(line.split("=",1) for line in (expected/".env.example").read_text().splitlines())
    values.update(MASTER_KEY=secrets.token_hex(16), ADMIN_PASSWORD=secrets.token_urlsafe(36)+"!aA1",
        ADMIN_USERNAME="experiment-admin", SESSION_SECRET=secrets.token_urlsafe(48),
        LOGIN_COOKIE_SECRET=secrets.token_urlsafe(48),
        DB_DSN="postgresql://zitadel:"+secrets.token_hex(32)+"@didasko_postgres:5432/zitadel?sslmode=disable",
        ISSUER="https://oidc.homolog.didasko.app.br", PUBLIC_URL="https://homolog.didasko.app.br/experimento",
        PROVISIONING_ORG_HEADER="x-zitadel-orgid", ORGANIZATION_CLAIM="urn:zitadel:iam:user:resourceowner:id")
    fd=os.open(destination, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"w") as output:
        output.write("".join(k+"="+v+"\n" for k,v in values.items()))
    print("Arquivo criado em modo 600; nenhum segredo exibido. Preencher IDs e claims apos bootstrap.")


if __name__ == "__main__": main()
