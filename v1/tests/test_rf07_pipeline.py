from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_rf07_rf13_rf14_compose_da_v1_nao_mexe_no_traefik():
    compose = (RAIZ / "deploy" / "docker-compose.v1-homolog.yml").read_text(encoding="utf-8")
    script = (RAIZ / "deploy" / "subir.sh").read_text(encoding="utf-8")
    imagem = (RAIZ / "deploy" / "app-v1.Dockerfile").read_text(encoding="utf-8")
    producao = (RAIZ / "deploy" / "docker-compose.producao.yml").read_text(encoding="utf-8")
    assert "name: homolog-v1" in compose
    assert "didasko_v1" in compose
    assert "extra_hosts:" in compose
    assert "oidc.homolog.didasko.app.br" in compose
    assert "TRAEFIK_EDGE_IP" in compose
    assert "mem_limit:" in compose
    assert "SEED_PASSWORD" not in compose
    assert "traefik:" not in compose
    assert "container_name: didasko_traefik" not in compose
    assert "exec -T -e SEED_PASSWORD" in script
    assert "-p homolog-v1" in script
    assert "--env-file .env.v1-homolog" in script
    assert "--env-file .env -f deploy/docker-compose.producao.yml" in script
    exemplo = (RAIZ / "deploy" / ".env.v1-homolog.example").read_text(encoding="utf-8")
    assert "POSTGRES_USER=didasko_v1" in exemplo
    assert "--force-recreate --no-deps app-v1" in script
    assert "--force-recreate --no-deps landing" in script
    assert "$COMPOSE up -d --build\n" in script
    assert "restart didasko_traefik" not in script
    assert "compose restart traefik" not in script
    assert "FROM python:3.12-slim" in imagem
    assert "python -m v1.landing_assets" in imagem
    assert "nodejs" not in imagem
    assert "image: traefik:latest" in producao


def test_rf_landing_compose_sem_banco_sem_rede_interna():
    compose = (RAIZ / "deploy" / "docker-compose.v1-homolog.yml").read_text(encoding="utf-8")
    script = (RAIZ / "deploy" / "subir.sh").read_text(encoding="utf-8")
    bloco = compose.split("  landing:", 1)[1].split("\nnetworks:", 1)[0]
    assert "DATABASE_URL" not in bloco
    assert "SESSION_SECRET" not in bloco
    assert "postgres-v1" not in bloco
    assert "interna" not in bloco
    assert "- borda" in bloco
    assert "v1.landing:create_app" in bloco
    assert "priority=100" in bloco
    assert "Path(`/homenagens`)" in bloco
    assert "PathPrefix(`/static/landing`)" in bloco
    assert "a landing nao pode receber DATABASE_URL" in script
    assert "https://homolog.didasko.app.br/" in script
    assert "https://homolog.didasko.app.br/homenagens" in script


def test_rf_landing_homenagens_existe_homolog_fora_do_roteador_de_producao():
    """A pagina permanece na app e na homologacao. O roteador de producao da v1
    (proposta de autorizacao) cobre so Path / e PathPrefix /static/landing;
    /homenagens, /login e o resto seguem na v0 (ARQUITECT, 22-23/10).
    """
    homolog = (RAIZ / "deploy" / "docker-compose.v1-homolog.yml").read_text(encoding="utf-8")
    producao = (RAIZ / "deploy" / "docker-compose.producao.yml").read_text(encoding="utf-8")
    app = (RAIZ / "v1" / "landing.py").read_text(encoding="utf-8")
    bloco = homolog.split("  landing:", 1)[1].split("\nnetworks:", 1)[0]
    assert 'Path(`/`)' in bloco
    assert 'Path(`/homenagens`)' in bloco
    assert "PathPrefix(`/static/landing`)" in bloco
    assert '@app.get("/homenagens")' in app
    assert "didasko-v1-landing" not in producao
    assert "Path(`/homenagens`)" not in producao
    assert "PathPrefix(`/static/landing`)" not in producao
    assert "so Path /" in homolog
    assert "seguem na v0" in producao


def test_rf07_fail_fast_se_postgres_user_nao_for_didasko_v1():
    script = (RAIZ / "deploy" / "subir.sh").read_text(encoding="utf-8")
    checagem = (
        '[ "$POSTGRES_USER" = "didasko_v1" ] || '
        '{ echo "ERRO: o .env.v1-homolog precisa de POSTGRES_USER=didasko_v1" >&2; exit 1; }'
    )
    assert checagem in script
    antes_do_up = script.split("$COMPOSE up -d --build postgres-v1", 1)[0]
    assert checagem in antes_do_up


def test_rf07_seed_nao_entra_no_environment_da_v0():
    producao = (RAIZ / "deploy" / "docker-compose.producao.yml").read_text(encoding="utf-8")
    assert "SEED_PASSWORD" not in producao
