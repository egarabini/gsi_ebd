import argparse
import json
import math
from pathlib import Path


def p95(samples):
    if len(samples) != 3 or any(not math.isfinite(x) or x <= 0 for x in samples):
        raise ValueError("Exatamente tres amostras positivas e finitas")
    # Nearest rank: com n=3, p95 e o maximo.
    return sorted(samples)[math.ceil(.95 * len(samples)) - 1]


def memory_bytes(value):
    units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
             "kB": 1000, "MB": 1000**2, "GB": 1000**3}
    for unit in sorted(units, key=len, reverse=True):
        if value.endswith(unit): return float(value[:-len(unit)].strip()) * units[unit]
    raise ValueError("Unidade desconhecida")


def summarize(path):
    raw = json.loads(Path(path).read_text())
    latency = [trial["seconds"] for trial in raw["trials"]]
    busy = all(trial["generation_started"] and trial["generation_overlap"] for trial in raw["trials"])
    idle = [row["provider_bytes"] for row in raw["memory"] if row["phase"] == "idle"]
    login = [row["provider_bytes"] for row in raw["memory"] if row["phase"] == "login"]
    if not idle or not login: raise ValueError("Repouso ou login nao medidos")
    return {"idle_provider_mb_max": max(idle)/1e6, "login_provider_mb_peak": max(login)/1e6,
            "login_seconds": latency, "p95_seconds": p95(latency),
            "e04": "PASS" if max(idle) < 1e9 else "FAIL",
            "e05": ("PASS" if p95(latency) <= 5 else "FAIL") if busy else "NAO_TESTADO",
            "ollama_overlap_all": busy}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("evidence")
    print(json.dumps(summarize(parser.parse_args().evidence), indent=2))
