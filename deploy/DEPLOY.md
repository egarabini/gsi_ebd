# Deploy do Didasko na VPS Contabo

Guia para colocar **didasko.app.br** no ar. Todos os comandos rodam na VPS,
como usuario `eduardo` (que ja esta no grupo `docker`).

---

## 1. Conferir o DNS

No painel do registro.br, o dominio `didasko.app.br` deve apontar para o IP da
VPS. Confira de fora:

```bash
dig +short didasko.app.br        # deve retornar o IP da VPS
```

Se ainda nao propagou, aguarde. O Let's Encrypt **precisa** que o dominio ja
aponte para o servidor, senao a emissao do certificado falha.

Confira tambem que as portas 80 e 443 estao liberadas no firewall.

---

## 2. Trazer o codigo

```bash
cd ~
git clone https://github.com/egarabini/gsi_ebd.git didasko
cd didasko
```

---

## 3. Configurar as variaveis

```bash
cp deploy/.env.producao.example .env
nano .env
```

Preencha, **gerando senhas fortes**:

```bash
openssl rand -base64 32   # use no POSTGRES_PASSWORD
openssl rand -hex 32      # use no SECRET_KEY
```

Preencha tambem o `ACME_EMAIL` (usado pelo Let's Encrypt) e o SMTP se quiser
email funcionando.

> O `.env` esta no `.gitignore` e no `.dockerignore`: ele **nao** vai para o
> GitHub nem para dentro da imagem.

---

## 4. Subir

```bash
docker compose -f deploy/docker-compose.producao.yml up -d --build
```

O primeiro build demora (instala dependencias Python e Node). Acompanhe:

```bash
docker compose -f deploy/docker-compose.producao.yml logs -f app
docker compose -f deploy/docker-compose.producao.yml ps
```

---

## 5. Popular o banco (primeira vez)

O seed cria admin, coordenador, instrutor, equipe, ambiente, alunos e o catalogo:

```bash
docker compose -f deploy/docker-compose.producao.yml exec app \
  python -m gsi_ebd.data.seed
```

Depois, **troque as senhas** dos usuarios de demonstracao (o seed cria todos com
`senha123`).

---

## 6. Verificar

```bash
curl -I https://didasko.app.br
```

Deve responder `200` com certificado valido. O Traefik emite o certificado na
primeira requisicao — se der erro de TLS, aguarde ~1 minuto e tente de novo.

Paginas publicas:
- `https://didasko.app.br/` — landing
- `https://didasko.app.br/homenagens` — homenagens
- `https://didasko.app.br/login` — acesso

---

## 7. Migrar o banco que ja existe

Se voce quiser trazer os dados do servidor antigo em vez de comecar do zero:

```bash
# no servidor ANTIGO: gerar o dump
pg_dump "postgresql://USUARIO:SENHA@localhost:5432/gsi_ebd" -f /tmp/gsi_ebd.sql

# copiar para a VPS nova
scp /tmp/gsi_ebd.sql eduardo@IP_NOVO:/tmp/

# na VPS nova: restaurar
docker compose -f deploy/docker-compose.producao.yml exec -T postgres \
  psql -U didasko -d didasko < /tmp/gsi_ebd.sql
```

> Atencao: se restaurar o dump **antigo**, ele traz o schema antigo
> (`gestor_id`/`supervisor_id`). Nesse caso rode depois o script de migracao:
> `docker compose ... exec app python migrar_producao.py --aplicar`

---

## Comandos do dia a dia

```bash
# ver logs
docker compose -f deploy/docker-compose.producao.yml logs -f app

# reiniciar so o app
docker compose -f deploy/docker-compose.producao.yml restart app

# atualizar o codigo
git pull && docker compose -f deploy/docker-compose.producao.yml up -d --build app

# backup do banco (recomendado agendar)
docker compose -f deploy/docker-compose.producao.yml exec -T postgres \
  pg_dump -U didasko didasko | gzip > ~/backup-didasko-$(date +%F).sql.gz

# parar tudo (sem apagar dados)
docker compose -f deploy/docker-compose.producao.yml down

# parar E APAGAR os dados (cuidado)
docker compose -f deploy/docker-compose.producao.yml down -v
```

---

## Observacoes

- **Postgres**: fica na rede interna do Docker, **sem porta exposta** ao mundo.
  Para acessar de fora, use um tunel SSH ou um `docker exec`.
- **HTTPS**: renovado automaticamente pelo Traefik.
- **Backup**: o volume `pgdata` guarda os dados. Agende o backup acima no cron.
- **Ollama**: nao esta neste compose. Se quiser a IA local depois, adicione um
  servico `ollama` com volume proprio.
