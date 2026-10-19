"""Verifica login/H-14 em HTTP real com banco e credenciais descartaveis."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from sqlmodel import Session
from v1.db import criar_engine
from v1.criar_usuario import criar_usuario
from gsi_ebd.models import Role


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidencia", type=Path)
    args = parser.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="dem011-v1-http-"))
    url = "sqlite:///" + (tmp / "didasko_v1.db").as_posix()
    with socket.socket() as local:
        local.bind(("127.0.0.1", 0))
        porta = local.getsockname()[1]
    ambiente = dict(os.environ, DATABASE_URL=url, SESSION_SECRET=secrets.token_urlsafe(48), COOKIE_SECURE="false")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "v1.main:create_app", "--factory", "--app-dir", str(ROOT),
        "--host", "127.0.0.1", "--port", str(porta)], cwd=ROOT / "v1", env=ambiente,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    engine = None
    resultado = {}
    def token(response):
        return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text).group(1)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{porta}", timeout=5) as client:
            for _ in range(150):
                if proc.poll() is not None:
                    raise RuntimeError("Servidor nao iniciou")
                try:
                    pagina = client.get("/login")
                    if pagina.status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError("Prazo esgotado")
            resultado["login_get"] = pagina.status_code
            engine = criar_engine(url)
            senha, nova = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            with Session(engine) as session:
                criar_usuario(session, "smoke@example.test", Role.ADMIN, senha)
            response = client.post("/login", data={"csrf_token": token(pagina), "email": "smoke@example.test", "senha": senha})
            resultado["login_post"] = response.status_code
            assert response.status_code == 303 and response.headers["location"] == "/perfil/alterar-senha"
            resultado["h14"] = client.get("/admin/obras").status_code
            assert resultado["h14"] == 403
            response = client.post("/perfil/alterar-senha", data={"csrf_token": token(client.get("/perfil/alterar-senha")),
                "senha_atual": senha, "nova_senha": nova, "confirma_senha": nova})
            resultado["troca"] = response.status_code
            assert response.status_code == 303
            resultado["admin"] = client.get("/admin/obras").status_code
            resultado["htmx"] = client.get("/static/htmx.min.js").status_code
            assert resultado["admin"] == resultado["htmx"] == 200
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        if engine is not None:
            engine.dispose()
    resultado["servidor_encerrado"] = proc.poll() is not None
    assert resultado["servidor_encerrado"]
    if args.evidencia:
        args.evidencia.write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(json.dumps(resultado))


if __name__ == "__main__":
    main()
