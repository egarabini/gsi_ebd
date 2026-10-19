import argparse
import json
import math
import statistics
from pathlib import Path


def login_metrics(samples):
    if len(samples) < 10 or any(not math.isfinite(x) or x <= 0 for x in samples):
        raise ValueError("Pelo menos dez amostras positivas e finitas")
    return {"median_seconds": statistics.median(samples), "max_seconds": max(samples)}


def memory_bytes(value):
    units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
             "kB": 1000, "MB": 1000**2, "GB": 1000**3}
    for unit in sorted(units, key=len, reverse=True):
        if value.endswith(unit): return float(value[:-len(unit)].strip()) * units[unit]
    raise ValueError("Unidade desconhecida")


def summarize(path):
    raw = json.loads(Path(path).read_text())
    latency = [trial["seconds"] for trial in raw["trials"]]
    metrics = login_metrics(latency)
    busy = all(trial["generation_started"] and trial["generation_overlap"] for trial in raw["trials"])
    idle = [row["provider_bytes"] for row in raw["memory"] if row["phase"] == "idle"]
    login = [row["provider_bytes"] for row in raw["memory"] if row["phase"] == "login"]
    if not idle or not login: raise ValueError("Repouso ou login nao medidos")
    return {"idle_provider_mb_max": max(idle)/1e6, "login_provider_mb_peak": max(login)/1e6,
            "login_seconds": latency, **metrics,
            "e04": "PASS" if max(idle) < 1e9 else "FAIL",
            "e05": ("PASS" if metrics["median_seconds"] <= 2 and metrics["max_seconds"] <= 5 else "FAIL") if busy else "NAO_TESTADO",
            "ollama_overlap_all": busy}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("evidence")
    print(json.dumps(summarize(parser.parse_args().evidence), indent=2))
