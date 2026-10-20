import os
import subprocess
from pathlib import Path


def main():
    expected = Path("/home/didasko-deploy/experimentos/didasko/experiments/zitadel")
    if os.name != "posix" or Path.cwd().resolve() != expected:
        raise SystemExit("Somente no diretorio autorizado da VPS, apos aprovacao d")
    destination = expected / ".env"
    values = dict(line.split("=",1) for line in (expected/".env.example").read_text().splitlines())
    def rand(*args):
        return subprocess.check_output(["openssl", "rand", *args], text=True).strip()
    db_password = rand("-hex", "32")
    values.update(MASTER_KEY=rand("-hex", "16"), ADMIN_PASSWORD=rand("-base64", "36")+"!aA1",
        ADMIN_USERNAME="experiment-admin", SESSION_SECRET=rand("-base64", "48"),
        LOGIN_COOKIE_SECRET=rand("-base64", "48"),
        DB_PASSWORD=db_password,
        DB_DSN="postgresql://zitadel:"+db_password+"@identity-db:5432/zitadel?sslmode=disable",
        ISSUER="https://oidc.homolog.didasko.app.br", PUBLIC_URL="https://homolog.didasko.app.br/experimento",
        PROVISIONING_ORG_HEADER="x-zitadel-orgid", ORGANIZATION_CLAIM="urn:zitadel:iam:user:resourceowner:id")
    fd=os.open(destination, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"w") as output:
        output.write("".join(k+"="+v+"\n" for k,v in values.items()))
    print("Arquivo criado em modo 600; nenhum segredo exibido. Preencher IDs e claims apos bootstrap.")


if __name__ == "__main__": main()
