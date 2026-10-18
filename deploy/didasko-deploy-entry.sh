#!/usr/bin/env bash
# ============================================================================
# Didasko - script de entrada do deploy pela VPS (comando forcado do SSH)
#
# Instalado em /usr/local/bin/didasko-deploy-entry (dono root, modo 755) e
# referenciado no authorized_keys do usuario didasko-deploy:
#
#   restrict,command="/usr/local/bin/didasko-deploy-entry" ssh-ed25519 AAAA...
#
# O SSH NAO executa o que o cliente pede: executa ESTE script. O pedido do
# cliente chega em $SSH_ORIGINAL_COMMAND e e validado aqui antes de qualquer
# coisa. Sem essa validacao o "restrict,command=" seria decorativo: quem tem a
# chave rodaria qualquer comando com o usuario de deploy.
#
# Uso (pela pipeline):  ssh ... "deploy v1.2.3"
#
# Ordem: backup do banco -> checkout da tag -> subir.sh -> verificacao HTTP.
# Para no primeiro erro. Log em ~/deploy-<data>.log.
#
# NAO e chamado pelo agente: quem chama e o GitHub Actions (ADR-010).
# ============================================================================
set -euo pipefail

REPO="$HOME/didasko"
BACKUPS="$HOME/backups"
LOG="$HOME/deploy-$(date +%Y%m%d-%H%M%S).log"
COMPOSE_ARQ="deploy/docker-compose.producao.yml"

# tudo o que sai vai para o log e para o stdout (a pipeline ve no run).
# O log() NAO usa tee: o exec abaixo ja espelha stdout/stderr no arquivo. Usar
# tee nas duas pontas gravaria cada linha duas vezes no log.
exec > >(tee -a "$LOG") 2>&1

log()   { echo "$(date -Is) $*"; }
morrer(){ log "[ERRO] $*"; exit 1; }

# ── 0. onde estamos ─────────────────────────────────────────────────────────
log "inicio"

# ── 1. validar o pedido ─────────────────────────────────────────────────────
CMD="${SSH_ORIGINAL_COMMAND:-}"
log "pedido recebido: '$CMD'"

case "$CMD" in
  deploy\ *) TAG="${CMD#deploy }" ;;
  *)         morrer "comando nao permitido. Use: deploy <tag>" ;;
esac
case "$TAG" in
  ''|*[!A-Za-z0-9._-]*) morrer "tag invalida: '$TAG'" ;;
esac
log "tag: $TAG"

[ -d "$REPO/.git" ] || morrer "clone nao encontrado em $REPO"
[ -f "$REPO/.env" ] || morrer ".env nao encontrado em $REPO"

cd "$REPO"

# ── 2. backup ANTES de tocar em qualquer coisa ──────────────────────────────
mkdir -p "$BACKUPS"
PGUSER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2 || echo didasko)
PGDB=$(grep '^POSTGRES_DB=' .env | cut -d= -f2 || echo didasko)
ARQ="$BACKUPS/didasko-$(date +%Y%m%d-%H%M%S).sql.gz"

log "backup do banco: $ARQ"
sudo -n docker compose --env-file .env -f "$COMPOSE_ARQ" \
  exec -T postgres pg_dump -U "$PGUSER" -d "$PGDB" | gzip > "$ARQ" \
  || morrer "pg_dump falhou - deploy ABORTADO antes de mexer no codigo"
[ -s "$ARQ" ] || morrer "backup vazio - deploy ABORTADO"
log "backup ok: $(du -h "$ARQ" | cut -f1)"

# retencao: mantem os 14 backups mais novos
ls -1t "$BACKUPS"/didasko-*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

# ── 3. checkout da tag exata ────────────────────────────────────────────────
log "buscando tags"
git fetch --tags --force || morrer "git fetch falhou"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null || morrer "tag $TAG nao existe no remoto"
git -c advice.detachedHead=false checkout --force "refs/tags/$TAG" || morrer "checkout falhou"
log "codigo em: $(git describe --tags --always)"

# ── 4. subir ────────────────────────────────────────────────────────────────
log "rodando subir.sh (sem import interativo)"
bash deploy/subir.sh --pular-import || morrer "subir.sh falhou"

# ── 5. verificacao final ────────────────────────────────────────────────────
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://didasko.app.br/ || echo 000)
  if [ "$CODE" = "200" ]; then
    log "[ok] site HTTP 200 em https://didasko.app.br/"
    log "[ok] deploy de $TAG concluido"
    exit 0
  fi
  sleep 3
done

morrer "site nao respondeu 200 depois do deploy (ultimo: $CODE). Rollback: git checkout <tag anterior> + bash deploy/subir.sh"
