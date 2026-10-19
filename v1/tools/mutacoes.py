"""Provas em copias fieis; nunca modifica os arquivos originais."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidencias", required=True, type=Path)
    args = parser.parse_args()
    if args.evidencias.exists():
        raise SystemExit("Use uma pasta de evidencias nova")
    origem = Path(__file__).resolve().parents[2]
    raiz = Path(tempfile.mkdtemp(prefix="dem011-fatia2-mutacao-"))
    casos = [("papel", "v1/routers/admin_obras.py", "test_rf02_matriz_rotas_servidor"),
             ("csrf", "v1/auth.py", "test_rf03_todos_posts_rejeitam_sem_csrf"),
             ("h14", "v1/auth.py", "test_h14_flag_bloqueia_todas_as_rotas_antes_da_troca")]
    resultados = []
    for nome, arquivo, seletor in casos:
        copia = raiz / nome
        copia.mkdir()
        for pasta in ("gsi_ebd", "v1"):
            shutil.copytree(origem / pasta, copia / pasta,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".env", "*.db"))
        shutil.copy2(origem / "rxconfig.py", copia / "rxconfig.py")
        cmd = [sys.executable, "-m", "pytest", "tests/test_seguranca.py", "-q", "-k", seletor,
               "--basetemp", str(raiz / (nome + "-base-tmp"))]
        base = subprocess.run(cmd, cwd=copia / "v1", text=True, capture_output=True)
        (raiz / (nome + "-baseline.log")).write_text(base.stdout + base.stderr, encoding="utf-8")
        assert base.returncode == 0, (nome, base.stdout[-2000:])
        print(nome + ": baseline verde", flush=True)
        alvo = copia / arquivo
        fonte = alvo.read_text(encoding="utf-8")
        if nome == "papel":
            fonte = fonte.replace("from v1.auth import exige", "from v1.auth import exige, usuario_atual")
            a = fonte.index("def lista(")
            b = fonte.index('\n\n@router.get("/admin/obras/nova")')
            trecho = fonte[a:b]
            assert trecho.count("Depends(ADMIN)") == 1
            fonte = fonte[:a] + trecho.replace("Depends(ADMIN)", "Depends(usuario_atual)") + fonte[b:]
        elif nome == "csrf":
            antes = 'if request.method == "POST":'
            assert fonte.count(antes) == 1
            fonte = fonte.replace(antes, "if False:")
        else:
            antes = 'if usuario and usuario.must_change_password and request.url.path not in {"/perfil/alterar-senha", "/logout"}:'
            assert fonte.count(antes) == 1
            fonte = fonte.replace(antes, "if False:")
        alvo.write_text(fonte, encoding="utf-8")
        cmd[-1] = str(raiz / (nome + "-mutante-tmp"))
        mutante = subprocess.run(cmd, cwd=copia / "v1", text=True, capture_output=True)
        (raiz / (nome + "-mutante.log")).write_text(mutante.stdout + mutante.stderr, encoding="utf-8")
        assert mutante.returncode == 1 and "failed" in mutante.stdout and "ERROR collecting" not in mutante.stdout, (nome, mutante.stdout[-2000:])
        r = {"mutacao": nome, "arquivo": arquivo, "seletor": seletor, "baseline_exit": base.returncode,
             "mutante_exit": mutante.returncode, "baseline": base.stdout.strip().splitlines()[-1],
             "mutante": mutante.stdout.strip().splitlines()[-1]}
        resultados.append(r)
        print(json.dumps(r), flush=True)
    args.evidencias.mkdir(parents=True)
    for arquivo in raiz.glob("*.log"):
        shutil.copy2(arquivo, args.evidencias / arquivo.name)
    (args.evidencias / "resultados.json").write_text(json.dumps(resultados, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
