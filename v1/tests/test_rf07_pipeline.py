from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_rf07_rf13_rf14_compose_da_v1_nao_mexe_no_traefik():
    compose = (RAIZ / "deploy" / "docker-compose.v1-homolog.yml").read_text(encoding="utf-8")
    script = (RAIZ / "deploy" / "subir.sh").read_text(encoding="utf-8")
    imagem = (RAIZ / "deploy" / "app-v1.Dockerfile").read_text(encoding="utf-8")
    producao = (RAIZ / "deploy" / "docker-compose.producao.yml").read_text(encoding="utf-8")
    assert "didasko_v1" in compose
    assert "extra_hosts:" in compose
    assert "oidc.homolog.didasko.app.br" in compose
    assert "TRAEFIK_EDGE_IP" in compose
    assert "mem_limit:" in compose
    assert "SEED_PASSWORD" not in compose
    assert "traefik:" not in compose
    assert "container_name: didasko_traefik" not in compose
    assert "exec -T -e SEED_PASSWORD" in script
    assert "--force-recreate --no-deps app-v1" in script
    assert "$COMPOSE up -d --build\n" in script
    assert "restart didasko_traefik" not in script
    assert "compose restart traefik" not in script
    assert "FROM python:3.12-slim" in imagem
    assert "nodejs" not in imagem
    assert "image: traefik:latest" in producao


def test_rf07_seed_nao_entra_no_environment_da_v0():
    producao = (RAIZ / "deploy" / "docker-compose.producao.yml").read_text(encoding="utf-8")
    assert "SEED_PASSWORD" not in producao
