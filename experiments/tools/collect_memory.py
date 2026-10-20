import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from experiments.tools.measure import memory_bytes


def sample(phase):
    ids = subprocess.check_output(["sudo", "-n", "docker", "ps", "-q", "--filter",
        "label=com.docker.compose.project=experimento-oidc"], text=True).split()
    if not ids: raise RuntimeError("Projeto do experimento nao encontrado")
    lines = subprocess.check_output(["sudo", "-n", "docker", "stats", "--no-stream", "--format", "{{json .}}", *ids], text=True).splitlines()
    rows = [json.loads(line) for line in lines]
    values = {row["Name"]: memory_bytes(row["MemUsage"].split("/")[0].strip()) for row in rows}
    if not all(any(name in key for key in values) for name in ("identity-api","identity-login","identity-app","identity-db")):
        raise RuntimeError("Conjunto incompleto")
    return {"utc": datetime.now(timezone.utc).isoformat(), "phase": phase,
            "containers_bytes": values, "provider_bytes": sum(v for k,v in values.items() if any(name in k for name in ("identity-api", "identity-login", "identity-db"))),
            "total_experiment_bytes": sum(values.values())}


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--phase", choices=["idle","login"], required=True)
    p.add_argument("--output", required=True); p.add_argument("--samples", type=int, default=10)
    args=p.parse_args()
    with Path(args.output).open("x", encoding="utf-8") as output:
        for _ in range(args.samples):
            output.write(json.dumps(sample(args.phase))+"\n"); output.flush(); time.sleep(1)
