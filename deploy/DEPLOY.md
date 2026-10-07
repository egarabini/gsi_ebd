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

## 5.5. Importar o conteúdo real (34 capítulos do Grudem)

O seed cria o catalogo com 5 estudos de exemplo (poucos parágrafos cada). O
material de verdade — 34 capítulos do *Doutrinas Cristãs* (Grudem), com 341
questões — vem do importador:

```bash
# 1. primeiro confira o que sera importado (NAO grava nada)
docker compose -f deploy/docker-compose.producao.yml exec app \
  python -m gsi_ebd.scripts.importar_estudo_dirigido --dry-run

# 2. veja as questoes de um capitulo, para conferir a qualidade
docker compose -f deploy/docker-compose.producao.yml exec app \
  python -m gsi_ebd.scripts.importar_estudo_dirigido --capitulo 1 --json

# 3. importar de verdade (grava no banco)
docker compose -f deploy/docker-compose.producao.yml exec app \
  python -m gsi_ebd.scripts.importar_estudo_dirigido --apply

# 4. ou importar para UM ambiente especifico
docker compose -f deploy/docker-compose.producao.yml exec app \
  python -m gsi_ebd.scripts.importar_estudo_dirigido --apply --ambiente 1
```

O importador e **idempotente**: rodar duas vezes nao duplica nem sobrescreve as
versoes ja criadas.

**O que ele grava:** um `Study` + `StudyVersion` por capítulo, com 12 questões
por capítulo (1 objetiva com gabarito, 1 de preenchimento e 10 abertas de
aquecimento, dissertação, reflexão e síntese).

**Importante:** sem `--apply` nada é gravado.

**Sobre o vínculo com o ambiente:** o catálogo é criado pelo Administrador e
depois *escolhido* por cada ambiente (`AmbienteEstudo`). Por padrão o importador
vincula os estudos a **todos os ambientes ativos** — sem esse vínculo o estudo
existiria no banco mas não apareceria para ninguém.

> O texto integral dos capítulos (tradução do livro) **não** é importado: por
> direitos autorais, a plataforma serve o plano de estudo (definições, passagens,
> objetivos e questões), que é autossuficiente.

---

---

## 5.6. Carregar o corpus bíblico (a Escritura da lição)

A tela da lição mostra o **texto bíblico verificado**, vindo do RAG local — não do
modelo. Isso evita alucinação em conteúdo doutrinário. Para isso o ChromaDB
precisa ter o corpus indexado.

O corpus e o script de carga estão no subprojeto **PASTOR_IA**
(`ESTUDOS_BIBLICOS/PASTOR_IA/`): a Almeida Corrigida Fiel de 2007, com os
comentários de Matthew Henry.

```bash
# 1. copiar o corpus e o script de carga para a VPS (do seu computador)
scp -r ESTUDOS_BIBLICOS/PASTOR_IA/rag/biblia \
       ESTUDOS_BIBLICOS/PASTOR_IA/requirements.txt \
       eduardo@IP_DA_VPS:~/didasko/corpus/

# ou, se preferir direto do GitHub (o corpus e um clone publico):
#   o BibleMarkdown vem de github.com/ameisehaufen/BibleMarkdown

# 2. instalar as dependencias de embeddings e carregar (na VPS)
docker compose -f deploy/docker-compose.producao.yml exec app \
  pip install -q chromadb sentence-transformers

docker compose -f deploy/docker-compose.producao.yml exec app \
  python /app/corpus/biblia/load_biblia.py --benchmark
```

O `--benchmark` roda o teste embutido: pergunta "O que João 3:16 diz?" e confere
se o versículo volta correto.

> **Enquanto o corpus não estiver carregado**, a lição funciona normalmente — o
> bloco de Escritura simplesmente não aparece. A integração degrada em silêncio,
> de propósito: nenhuma lição quebra por causa do RAG.

### Sobre o LLM (opcional)

O `Ollama` **não** está neste compose. Sem ele, a Escritura aparece normalmente
(ela vem do corpus, não do modelo); só os recursos de explicação por IA ficam
inativos. Se quiser ligá-los, suba um serviço Ollama com volume próprio e aponte
`OLLAMA_BASE_URL` para ele.

---

---

## 5.7. Ligar a IA local (Ollama)

O Ollama aparece em dois lugares do produto:

1. **Parecer preliminar** das respostas abertas, na tela `/revisao` — o instrutor
   clica em "Sugerir com IA", a IA prepara um parecer, e **o instrutor revisa,
   edita ou descarta** antes de enviar ao aluno.
2. Explicações de contexto (quando ligadas).

> **A Escritura não vem do modelo.** O texto bíblico vem do corpus no ChromaDB
> (seção 5.6). O modelo é instruído a não citar versículo de memória — é assim
> que se evita alucinação em conteúdo doutrinário.

### Baixar o modelo (uma vez, depois de subir)

```bash
docker compose -f deploy/docker-compose.producao.yml exec ollama \
  ollama pull llama3
```

Confira que baixou:

```bash
docker compose -f deploy/docker-compose.producao.yml exec ollama ollama list
```

### Sobre o tamanho do modelo

O VPS tem **12 GB de RAM**. O `llama3` (8B, ~4,7 GB) roda com folga. Modelos
grandes (70B) **não cabem** — evite.

Se quiser um modelo melhor em português, `mistral-nemo` ou `gemma2:9b` são boas
alternativas; troque o `OLLAMA_MODEL` no `.env` e baixe o correspondente.

### Sem o Ollama

Se o serviço estiver parado, **nada quebra**: o botão "Sugerir com IA" mostra
"Ollama não respondeu" e o instrutor escreve o parecer normalmente. A IA é um
apoio, não uma dependência.

---

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
