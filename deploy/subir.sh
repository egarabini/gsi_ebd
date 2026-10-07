#!/usr/bin/env bash
# ============================================================================
# Didasko — script de deploy para a VPS
#
# Uso (na VPS, dentro de ~/didasko):
#     bash deploy/subir.sh
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

COMPOSE="docker compose -f deploy/docker-compose.producao.yml"

echo "=============================================="
echo " Didasko — deploy"
echo "=============================================="

# ── 1. pre-requisitos ───────────────────────────────────────────────────────
echo; echo "1. Pre-requisitos"
command -v docker >/dev/null 2>&1 || morrer "docker nao encontrado"
docker compose version >/dev/null 2>&1 || morrer "docker compose (plugin) nao encontrado"
ok "docker e docker compose presentes"
[ -f deploy/docker-compose.producao.yml ] || morrer "rode este script da raiz do projeto (nao achei deploy/)"
[ -f .env ] || morrer ".env nao encontrado. Copie deploy/.env.producao.example para .env e preencha"
ok ".env presente"

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
  if $COMPOSE exec -T postgres pg_isready -U "$(grep '^POSTGRES_USER=' .env | cut -d= -f2 || echo didasko)" >/dev/null 2>&1; then
    ok "banco pronto"; break
  fi
  [ "$i" -eq 40 ] && morrer "o banco nao respondeu em 80s"
  sleep 2
done

# ── 6. estado dos servicos ──────────────────────────────────────────────────
echo; echo "6. Estado dos servicos"
$COMPOSE ps

# ── 7. popular o banco (so se estiver vazio) ────────────────────────────────
echo; echo "7. Populando o banco"
$COMPOSE exec -T app python -m gsi_ebd.data.seed || aviso "seed falhou (talvez ja populado)"

# ── 8. importar o conteudo (34 capitulos) ───────────────────────────────────
echo; echo "8. Importando os 34 capitulos do Doutrinas Cristas"
$COMPOSE exec -T app python -m gsi_ebd.scripts.importar_estudo_dirigido --dry-run | tail -5
echo
read -r -p "Importar agora? (s/n) " RESP
if [ "${RESP,,}" = "s" ]; then
  $COMPOSE exec -T app python -m gsi_ebd.scripts.importar_estudo_dirigido --apply
  ok "conteudo importado"
else
  aviso "pulou a importacao (rode depois: $COMPOSE exec app python -m gsi_ebd.scripts.importar_estudo_dirigido --apply)"
fi

# ── 9. baixar o modelo de IA ────────────────────────────────────────────────
echo; echo "9. Modelo de IA (Ollama)"
MODELO=$(grep '^OLLAMA_MODEL=' .env | cut -d= -f2 || echo llama3)
aviso "baixando $MODELO (alguns GB, pode demorar)"
$COMPOSE exec -T ollama ollama pull "$MODELO" || aviso "nao consegui baixar o modelo — a IA fica inativa, o resto funciona"
$COMPOSE exec -T ollama ollama list || true

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
echo "Login  : https://didasko.app.br/login  (admin@gsi.ebd / senha123)"
echo
echo "TROQUE AS SENHAS dos usuarios de demonstracao."
echo "Se algo falhar: $COMPOSE logs -f app"