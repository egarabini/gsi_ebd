import argparse
import asyncio
import getpass
import json
import os
from urllib.parse import urlsplit
import time
from pathlib import Path

import httpx


def read_credentials(path):
    if path:
        file = Path(path)
        if os.name == "posix" and file.stat().st_mode & 0o077:
            raise ValueError("Arquivo de credenciais deve ser privado (600)")
        return json.loads(file.read_text())
    return {"username": getpass.getpass("Usuario de teste (nao registrado): "),
            "password": getpass.getpass("Senha ja alterada (nao registrada): "),
            "basic_username": getpass.getpass("Usuario Basic Auth (nao registrado): "),
            "basic_password": getpass.getpass("Senha Basic Auth (nao registrada): ")}


async def measure(args):
    from playwright.async_api import async_playwright
    if args.trials < 10:
        raise ValueError("O criterio exige pelo menos dez logins")
    credentials = read_credentials(args.credentials_file)
    origin = urlsplit(args.public_url)
    basic = {"username": credentials["basic_username"], "password": credentials["basic_password"],
             "origin": origin.scheme + "://" + origin.netloc}
    results = []
    async with async_playwright() as pw, httpx.AsyncClient(timeout=None) as http:
        browser = await pw.chromium.launch(headless=True)
        try:
            for _ in range(args.trials):
                started = asyncio.Event(); finished = asyncio.Event()
                async def generate():
                    async with http.stream("POST", args.ollama_url + "/api/generate", json={
                        "model": args.model, "prompt": "Explain matrix multiplication in detail.",
                        "stream": True, "options": {"num_predict": 4096}}) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line and json.loads(line).get("response"): started.set()
                    finished.set()
                task = asyncio.create_task(generate())
                context = await browser.new_context(http_credentials=basic)
                try:
                    await asyncio.wait_for(started.wait(), timeout=180)
                    page = await context.new_page(); before = time.perf_counter()
                    await page.goto(args.public_url + "/login")
                    await page.locator(args.username_selector).fill(credentials["username"])
                    await page.locator(args.username_submit).click()
                    await page.locator(args.password_selector).fill(credentials["password"])
                    await page.locator(args.password_submit).click()
                    await page.wait_for_url(args.public_url + "/me", timeout=60000)
                    identity = json.loads(await page.locator("body").inner_text())
                    if not all(identity.get(key) for key in ("subject", "role", "environment")):
                        raise RuntimeError("Login nao confirmou a identidade")
                    elapsed = time.perf_counter()-before
                    results.append({"seconds": elapsed, "generation_started": started.is_set(),
                                    "generation_overlap": not finished.is_set() and not task.done()})
                finally:
                    task.cancel(); await asyncio.gather(task, return_exceptions=True)
                    await context.close()
        finally:
            await browser.close()
            Path(args.output).write_text(json.dumps({"trials": results}, indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--public-url", required=True)
    p.add_argument("--ollama-url", default="http://127.0.0.1:11434"); p.add_argument("--model", default="gemma2:9b")
    for key in ("username-selector", "username-submit", "password-selector", "password-submit"):
        p.add_argument("--"+key, required=True)
    p.add_argument("--trials", type=int, default=10)
    p.add_argument("--credentials-file")
    p.add_argument("--output", required=True)
    try:
        asyncio.run(measure(p.parse_args()))
    except Exception:
        raise SystemExit("Medicao interrompida; conferir infraestrutura e evidencia parcial, sem registrar credenciais.") from None
