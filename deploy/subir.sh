#!/usr/bin/env bash
# ============================================================================
# Didasko — script de deploy para a VPS
#
# Uso (na VPS, dentro de ~/didasko):
#     bash deploy/subir.sh
# Homologacao da v1 (compose proprio; nao reinicia o Traefik):
#     bash deploy/subir.sh --v1
#
# Faz tudo com verificacao em cada passo e PARA no primeiro erro, em vez de
# seguir e deixar o site meio no ar.
# ============================================================================
set -euo pipefail

VERDE='\033[0;32m'; VERM='\033[0;31m'; AMAR='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "${VERDE}[ok]${NC} $1"; }
erro() { echo -e "${VERM}[ERRO]${NC} $1"; }
aviso(){ echo -e "${AMAR}[..]${NC} $1"; }
morrer(){ erro "$1"; exit 1; }

echo "=============================================="
echo " Didasko — deploy"
echo "=============================================="

# O compose procura o .env NA PASTA DO ARQUIVO COMPOSE (deploy/), nao na raiz.
# Como o .env fica na raiz, e obrigatorio passar --env-file explicitamente —
# sem isso as variaveis chegam VAZIAS (POSTGRES_PASSWORD em branco, sem ACME_EMAIL)
# e o Docker so emite um WARN, o que e facil de nao perceber.
#
# ACESSO AO DOCKER: o usuario provisionado para deploy (didasko-deploy) NAO esta no
# grupo docker — o acesso dele e `sudo -n /usr/bin/docker`, por regra NOPASSWD.
# Quem entra como eduardo tem acesso direto. Antes o script assumia acesso direto e
# morria no primeiro comando que fala com o daemon, mesmo com todo o resto certo
# (o `docker --version` funciona sem socket, entao a falha aparecia tarde).
if docker info >/dev/null 2>&1; then
  DOCKER="docker"
elif sudo -n docker info >/dev/null 2>&1; then
  DOCKER="sudo -n docker"
else
  morrer "sem acesso ao daemon do Docker (nem direto, nem via 'sudo -n docker')"
fi

COMPOSE="$DOCKER compose --env-file .env -f deploy/docker-compose.producao.yml"

# Opcoes, para deploy automatizado (sem terminal):
#   --forcar-seed    roda o seed mesmo com o banco ja populado
#   --importar       aplica a importacao do conteudo sem perguntar
#   --pular-import   nao importa (e o padrao quando nao ha terminal)
#   --v1             sobe so a homologacao da v1
FORCAR_SEED=0
IMPORTAR=""
ALVO_V1=0
for arg in "$@"; do
  case "$arg" in
    --forcar-seed)  FORCAR_SEED=1 ;;
    --importar)     IMPORTAR="s" ;;
    --pular-import) IMPORTAR="n" ;;
    --v1)           ALVO_V1=1 ;;
    *) aviso "argumento ignorado: $arg" ;;
  esac
done

# A-2: a senha do seed vem do ambiente do script. Nao entra no environment: do compose.
carregar_seed_password() {
  if [ -n "${SEED_PASSWORD:-}" ]; then
    return 0
  fi
  if [ -f .env ] && grep -q '^SEED_PASSWORD=.\+' .env; then
    SEED_PASSWORD="$(grep '^SEED_PASSWORD=' .env | head -1 | cut -d= -f2-)"
    export SEED_PASSWORD
  fi
}

semear() {
  local servico="$1"
  carregar_seed_password
  if [ -z "${SEED_PASSWORD:-}" ]; then
    morrer "SEED_PASSWORD ausente no ambiente deste script. Nao grave a senha no environment do compose."
  fi
  # A v0 trata falha do seed como aviso: o site da producao nao pode cair por isso.
  $COMPOSE exec -T -e SEED_PASSWORD "$servico" python -m gsi_ebd.data.seed < /dev/null || aviso "seed falhou"
}

semear_estrito() {
  local servico="$1"
  carregar_seed_password
  if [ -z "${SEED_PASSWORD:-}" ]; then
    morrer "SEED_PASSWORD ausente no ambiente deste script. Nao grave a senha no environment do compose."
  fi
  $COMPOSE exec -T -e SEED_PASSWORD "$servico" python -m gsi_ebd.data.seed < /dev/null \
    || morrer "seed da v1 falhou"
}

subir_v1() {
  echo " Didasko — homologacao v1"
  COMPOSE="$DOCKER compose --env-file .env -f deploy/docker-compose.v1-homolog.yml"
  [ -f deploy/docker-compose.v1-homolog.yml ] || morrer "compose da v1 ausente"
  [ -f .env ] || morrer ".env nao encontrado"
  faltando=()
  grep -q '^POSTGRES_PASSWORD=.\+' .env || faltando+=("POSTGRES_PASSWORD")
  grep -q '^POSTGRES_USER=.\+' .env || faltando+=("POSTGRES_USER")
  grep -q '^SESSION_SECRET=.\+' .env || faltando+=("SESSION_SECRET")
  grep -q '^TRAEFIK_EDGE_IP=.\+' .env || faltando+=("TRAEFIK_EDGE_IP")
  [ ${#faltando[@]} -eq 0 ] || morrer "faltam no .env: ${faltando[*]}"
  SECRET="$(grep '^SESSION_SECRET=' .env | head -1 | cut -d= -f2-)"
  [ "${#SECRET}" -ge 32 ] || morrer "SESSION_SECRET precisa de 32 caracteres ou mais"
  unset SECRET

  echo; echo "4. Postgres proprio da v1 (didasko_v1)"
  $COMPOSE up -d --build postgres-v1
  PGUSER="$(grep '^POSTGRES_USER=' .env | cut -d= -f2)"
  for i in $(seq 1 40); do
    if $COMPOSE exec -T postgres-v1 pg_isready -U "$PGUSER" -d didasko_v1 >/dev/null 2>&1 < /dev/null; then
      ok "banco didasko_v1 pronto"; break
    fi
    [ "$i" -eq 40 ] && morrer "o postgres da v1 nao respondeu em 80s"
    sleep 2
  done

  # force-recreate so da app. Recriar o compose da v0 reiniciaria o Traefik.
  echo; echo "5. App da v1"
  $COMPOSE up -d --build --force-recreate --no-deps app-v1
  URL="$($COMPOSE exec -T app-v1 printenv DATABASE_URL < /dev/null || true)"
  case "$URL" in
    *didasko_v1*) ok "DATABASE_URL aponta para didasko_v1" ;;
    *) unset URL; morrer "DATABASE_URL da v1 nao aponta para didasko_v1" ;;
  esac
  unset URL

  echo; echo "7. Seed da v1 (so se o banco estiver vazio)"
  USUARIOS="$(
    $COMPOSE exec -T postgres-v1 psql -U "$PGUSER" -d didasko_v1 \
      -tAc 'select count(*) from "user";' 2>/dev/null < /dev/null | tr -d '[:space:]' || true
  )"
  if [ "${USUARIOS:-0}" = "0" ] || [ "$FORCAR_SEED" = "1" ]; then
    semear_estrito app-v1
    ok "seed da v1 concluido"
  else
    aviso "banco ja tem ${USUARIOS} usuarios — pulando o seed"
  fi

  echo; echo "10. HTTP da homologacao"
  for i in $(seq 1 12); do
    CODIGO="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://homolog.didasko.app.br/login || echo 000)"
    if [ "$CODIGO" = "200" ]; then
      ok "https://homolog.didasko.app.br/login respondeu 200"
      return 0
    fi
    aviso "tentativa $i/12: HTTP $CODIGO"
    sleep 10
  done
  morrer "sem HTTP 200. O script ja recriou so a app-v1. Se persistir, pare e devolva ao PLANNER. Nao reinicie o Traefik."
}

if [ "$ALVO_V1" = "1" ]; then
  subir_v1
  exit 0
fi

# ── 1. pre-requisitos ───────────────────────────────────────────────────────
echo; echo "1. Pre-requisitos"
command -v docker >/dev/null 2>&1 || morrer "docker nao encontrado"
docker compose version >/dev/null 2>&1 || morrer "docker compose (plugin) nao encontrado"
ok "docker e docker compose presentes"
ok "acesso ao daemon: $DOCKER"
[ -f deploy/docker-compose.producao.yml ] || morrer "rode este script da raiz do projeto (nao achei deploy/)"
[ -f .env ] || morrer ".env nao encontrado. Copie deploy/.env.producao.example para .env e preencha"
ok ".env presente"

# O compose monta ../conteudo/ESTUDOS_BIBLICOS (relativo a deploy/) em /conteudo.
# O conteudo vive em OUTRO repositorio (EVANGELICOS), clonado em conteudo/.
# Se a ORIGEM do bind mount nao existir, o Docker NAO falha: ele cria um
# diretorio VAZIO. O erro so aparece depois, no importador, como
# "nao contem DOUTRINAS_CRISTAS. Conteudo encontrado: []" — foi o que aconteceu
# no primeiro deploy, e custou uma rodada inteira de diagnostico.
CONTEUDO="conteudo/ESTUDOS_BIBLICOS"
CONTEUDO_ALVO="$CONTEUDO/DOUTRINAS_CRISTAS/estudo_dirigido"
if [ ! -d "$CONTEUDO_ALVO" ]; then
  aviso "$CONTEUDO_ALVO nao encontrado"
  if [ -d conteudo/.git ]; then
    morrer "existe um clone em conteudo/ mas sem a arvore esperada. Confira: git -C conteudo status"
  fi
  aviso "clonando o repositorio de conteudo (EVANGELICOS, publico) em conteudo/"
  git clone --depth 1 https://github.com/egarabini/EVANGELICOS.git conteudo \
    || morrer "nao consegui clonar o conteudo. Clone na mao: git clone https://github.com/egarabini/EVANGELICOS.git conteudo"
  [ -d "$CONTEUDO_ALVO" ] || morrer "o clone nao trouxe $CONTEUDO_ALVO"
fi
ok "conteudo presente em $CONTEUDO"

# ── 2. variaveis obrigatorias ───────────────────────────────────────────────
echo; echo "2. Variaveis obrigatorias"
faltando=()
grep -q '^ACME_EMAIL=.\+' .env        || faltando+=("ACME_EMAIL")
grep -q '^POSTGRES_PASSWORD=.\+' .env || faltando+=("POSTGRES_PASSWORD")
grep -q '^SECRET_KEY=.\+' .env        || faltando+=("SECRET_KEY")
if grep -q 'troque-por' .env; then
  aviso "ainda ha valores 'troque-por...' no .env"
fi
[ ${#faltando[@]} -eq 0 ] || morrer "faltam no .env: ${faltando[*]}"
ok "ACME_EMAIL, POSTGRES_PASSWORD e SECRET_KEY definidos"

# confirma que o COMPOSE (nao so o shell) esta enxergando as variaveis
CONFIG_TESTE=$($COMPOSE config 2>/dev/null | grep -c 'POSTGRES_PASSWORD: ""' || true)
if [ "${CONFIG_TESTE:-0}" != "0" ]; then
  morrer "o compose nao esta lendo o .env (POSTGRES_PASSWORD chegou vazio)"
fi
ok "o compose esta lendo o .env corretamente"

# ── 3. DNS ──────────────────────────────────────────────────────────────────
echo; echo "3. DNS do dominio"
IP_VPS=$(curl -fsS --max-time 10 https://api.ipify.org 2>/dev/null || echo "?")
IP_DNS=$(getent hosts didasko.app.br | awk '{print $1}' | head -1 || echo "?")
aviso "IP desta VPS: $IP_VPS | IP do DNS: $IP_DNS"
if [ "$IP_VPS" != "?" ] && [ "$IP_DNS" != "?" ] && [ "$IP_VPS" != "$IP_DNS" ]; then
  aviso "o DNS NAO aponta para esta VPS — o Let's Encrypt vai falhar na emissao"
  aviso "corrija no registro.br antes de continuar (ou siga e resolva depois)"
else
  ok "DNS aponta para esta VPS"
fi

# ── 4. subir ────────────────────────────────────────────────────────────────
echo; echo "4. Subindo os servicos (o primeiro build demora varios minutos)"
$COMPOSE up -d --build
ok "containers criados"

# ── 5. esperar o banco ──────────────────────────────────────────────────────
echo; echo "5. Aguardando o banco responder"
for i in $(seq 1 40); do
  if $COMPOSE exec -T postgres pg_isready -U "$(grep '^POSTGRES_USER=' .env | cut -d= -f2 || echo didasko)" >/dev/null 2>&1 < /dev/null; then
    ok "banco pronto"; break
  fi
  [ "$i" -eq 40 ] && morrer "o banco nao respondeu em 80s"
  sleep 2
done

# ── 6. estado dos servicos ──────────────────────────────────────────────────
echo; echo "6. Estado dos servicos"
$COMPOSE ps

# o app precisa estar DE PE antes de rodar seed/import (exec -T falha se ele
# estiver reiniciando — foi o que aconteceu no primeiro deploy)
echo; echo "6b. Confirmando que o app esta de pe"
APP_OK=0
for i in $(seq 1 30); do
  ESTADO=$($COMPOSE ps --format json app 2>/dev/null | grep -o '"State":"[a-z]*"' | head -1 || echo "")
  if echo "$ESTADO" | grep -q running; then
    # running nao basta: pode estar em loop de restart. Testa se responde.
    if $COMPOSE exec -T app python -c "import gsi_ebd.gsi_ebd" >/dev/null 2>&1 < /dev/null; then
      APP_OK=1; ok "app de pe e o codigo importa"; break
    fi
  fi
  aviso "tentativa $i/30: app ainda nao esta pronto"
  sleep 4
done

if [ "$APP_OK" != "1" ]; then
  erro "o app NAO subiu. Logs:"
  $COMPOSE logs --tail 40 app || true
  morrer "corrija o app antes de popular o banco (seed e import dependem dele)"
fi

# ── 7. popular o banco (so se estiver vazio) ────────────────────────────────
echo; echo "7. Populando o banco"
PGUSER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2 || echo didasko)
PGDB=$(grep '^POSTGRES_DB=' .env | cut -d= -f2 || echo didasko)
USUARIOS=$(
  $COMPOSE exec -T postgres psql -U "${PGUSER:-didasko}" -d "${PGDB:-didasko}" \
    -tAc 'select count(*) from "user";' 2>/dev/null < /dev/null | tr -d '[:space:]' || true
)
if [ "${USUARIOS:-0}" = "0" ]; then
  semear app
  ok "banco populado"
else
  # O titulo desta secao sempre disse "so se estiver vazio", mas o comando rodava
  # SEMPRE. Nao e inofensivo: seed_site_config ATUALIZA as chaves existentes para
  # os valores do codigo (seed.py:179-186), entao num banco em uso ele desfaz
  # ajustes feitos pelo painel. O resto do seed e guardado e nao duplicaria nada,
  # mas o efeito nas chaves de site_config e real.
  aviso "banco ja tem ${USUARIOS} usuarios — pulando o seed (use --forcar-seed para rodar assim mesmo)"
  if [ "$FORCAR_SEED" = "1" ]; then
    aviso "forcando o seed"
    semear app
  fi
fi

# ── 8. importar o conteudo (34 capitulos) ───────────────────────────────────
echo; echo "8. Importando os 34 capitulos do Doutrinas Cristas"

# Confirma que o CONTAINER enxerga o conteudo. O Docker nao avisa quando o bind
# mount resolve para uma pasta inexistente: cria uma vazia e segue. Testar de
# dentro do container e o unico jeito confiavel de saber que o mount valeu.
$COMPOSE exec -T app test -d /conteudo/ESTUDOS_BIBLICOS/DOUTRINAS_CRISTAS/estudo_dirigido < /dev/null \
  || morrer "/conteudo/ESTUDOS_BIBLICOS chegou VAZIO no container (bind mount sem origem). Veja o caminho resolvido com: $COMPOSE config | grep -A4 'volumes:'"
ok "o container enxerga o conteudo em /conteudo/ESTUDOS_BIBLICOS"

$COMPOSE exec -T app python -m gsi_ebd.scripts.importar_estudo_dirigido --dry-run < /dev/null | tail -5
echo

# O prompt so faz sentido com terminal. Sem terminal (deploy automatizado, cron,
# nohup), `read` recebe EOF, devolve != 0 e o `set -e` ENCERRA O SCRIPT EM
# SILENCIO — foi exatamente o que aconteceu no deploy de 2026-10-16: o log parou
# aqui, sem uma linha de erro, e os passos 9 e 10 nunca rodaram.
# Agravante: `docker compose exec -T` tambem consome o stdin do script (compose
# v5.6.0), entao a resposta podia ser engolida por um exec anterior — por isso
# todos os execs acima redirecionam < /dev/null.
RESP="${IMPORTAR:-n}"
if [ -z "$IMPORTAR" ]; then
  if [ -t 0 ]; then
    read -r -p "Importar agora? (s/n) " RESP || RESP="n"
  else
    aviso "sem terminal: nao vou importar (use --importar para aplicar)"
  fi
fi
if [ "${RESP,,}" = "s" ]; then
  $COMPOSE exec -T app python -m gsi_ebd.scripts.importar_estudo_dirigido --apply < /dev/null
  ok "conteudo importado"
else
  aviso "pulou a importacao (rode depois: $COMPOSE exec app python -m gsi_ebd.scripts.importar_estudo_dirigido --apply)"
fi

# ── 9. baixar o modelo de IA ────────────────────────────────────────────────
echo; echo "9. Modelo de IA (Ollama)"
MODELO=$(grep '^OLLAMA_MODEL=' .env | cut -d= -f2 || echo llama3)
aviso "baixando $MODELO (alguns GB, pode demorar)"
$COMPOSE exec -T ollama ollama pull "$MODELO" < /dev/null || aviso "nao consegui baixar o modelo — a IA fica inativa, o resto funciona"
$COMPOSE exec -T ollama ollama list < /dev/null || true

# ── 10. verificar o site ────────────────────────────────────────────────────
echo; echo "10. Verificando o site"
sleep 5
for i in $(seq 1 12); do
  CODIGO=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://didasko.app.br/ || echo "000")
  if [ "$CODIGO" = "200" ]; then ok "https://didasko.app.br respondeu 200"; break; fi
  aviso "tentativa $i/12: HTTP $CODIGO (o certificado pode levar ~1 min)"
  [ "$i" -eq 12 ] && aviso "ainda nao respondeu 200 — veja os logs abaixo"
  sleep 10
done

echo; echo "Logs recentes do app:"
$COMPOSE logs --tail 25 app || true

echo
echo "=============================================="
ok "Deploy concluido"
echo "=============================================="
echo "Site   : https://didasko.app.br"
echo "Homena.: https://didasko.app.br/homenagens"
echo
echo "TROQUE AS SENHAS dos usuarios de demonstracao."
echo "Se algo falhar: $COMPOSE logs -f app"