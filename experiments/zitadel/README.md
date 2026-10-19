# DEM-016: experimento isolado de identidade

**Nao adotado. Infraestrutura ainda nao autorizada.** Nenhum comando abaixo deve ser aplicado na VPS antes da aprovacao a-e. Nao altera v0, v1, RF01 ou flow.py.

## Fase 1

Da raiz do worktree, com Python 3.12 e um ambiente virtual proprio:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r experiments/zitadel/requirements-test.txt
.venv/Scripts/python -m pytest experiments/tests -q
docker compose -f experiments/zitadel/docker-compose.yml config --no-interpolate --quiet
```

O cliente esta em `experiments/identity_client/`, a interface e `IdentityProvider -> Identity(subject, role, environment)`. A implementacao le somente claims ja validados por Authlib. O contrato pode ser substituido sem mudar o consumidor. Roles, nome do claim da organizacao, scopes e header de provisao sao configuraveis. A API de provisao e um adaptador de contrato especifico, nao uma promessa de portabilidade automatica de APIs administrativas.

Todos os valores em `.env.example` sao vazios. `ISSUER`, `PUBLIC_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `SESSION_SECRET`, `ORGANIZATION_ID`, `PROJECT_ID`, `ENVIRONMENT`, `SCOPES`, `ORGANIZATION_CLAIM`, `ROLES_CLAIM`, `PROVISIONING_ORG_HEADER`, `PROVISIONING_TOKEN` configuram o cliente. OIDC confidencial usa secret basic; client publico usa PKCE sem secret. Ambos exigem S256. Cookies Secure/HttpOnly/SameSite=lax, tokens apenas no servidor, sessao de 10 minutos, um worker. Logout e local; nao afirma logout global/revogacao do provedor. Sem senha propria nem redirect proprio de troca obrigatoria.

Rotas externas: `/experimento/health`, `/login`, `/callback`, `/me`, POST `/logout`, POST `/instructors` (todas sob `/experimento`). O Traefik retira o prefixo e o FastAPI conhece seu root_path. `/instructors` exige coordenador, token CSRF de `/me` em `X-CSRF-Token` e Origin da app, diferente do emissor. JSON: email, first_name, last_name, initial_password. A senha vai somente ao provedor, nao aparece na resposta/log da app. Email de teste marcado verificado: nao ha email real nem convite neste ensaio. O grant instrutor e feito apos criar usuario; erro parcial retorna 502 e exige conciliacao, sem apagar usuario automaticamente.

## Configuracao revisavel da homologacao

- Clone: `/home/didasko-deploy/experimentos/didasko/`; projeto obrigatorio `experimento-oidc`.
- API `ghcr.io/zitadel/zitadel:v4.19.5`, 512 MiB; Login V2 `ghcr.io/zitadel/zitadel-login:v4.19.5`, 256 MiB; cliente 128 MiB. Imagens fixas por tag, digests do indice oficial consultados sem baixar camadas: API sha256:a586456a208e0db4c633db0ba43c427c24b37846138b8b13ff16ad8e003a18d3; Login sha256:2f8e57672fcd4f9a285d99355fae9f85fd7495768c090c07c3bbc2d84fc06617. Confirmar que as tags ainda apontam a estes digests antes de executar. Nenhuma imagem foi baixada/executada para homologacao na fase 1.
- Rede externa `deploy_didasko`; sem porta publicada, Postgres novo ou volume da v0.
- API h2c:8080 no host `oidc.homolog.didasko.app.br`; Login V2 HTTP:3000 no mesmo host com prioridade maior em `/ui/v2/login`; app:8000 em `Host(homolog.didasko.app.br) && PathPrefix(/experimento)`. TLS no Traefik, websecure, certresolver `le` existente (httpchallenge; nenhuma alteracao global no Traefik).
- API executa como 1000:1000; Login V2 como 1001:1001 (UID oficial Next.js). O volume nomeado `experimento-oidc_bootstrap` precisa de diretorio 1000:1001 modo 2750 **antes** do primeiro start; apos a API gerar o PAT, ajustar somente esse arquivo para 1000:1001 modo 0640, antes de iniciar o Login. Preparacao unica e restrita ao volume novo, a aprovar; sem processo root permanente. O PAT do Login fica nesse volume, nunca no repositorio. A compatibilidade destes UIDs e o bootstrap so serao confirmados no ensaio real; se nao funcionar, registrar, nao remover a restricao silenciosamente.
- Banco/papel `zitadel` no `didasko_postgres`. DSN final com esse papel, nunca admin do Postgres no container. DSN e suportado na tag escolhida e exige banco/usuario ja existentes. **PUBLIC CONNECT pode permitir acesso a didasko**: verificar ACL e HBA. Nao revogar PUBLIC do banco da v0. Se necessario, aprovar regras HBA anteriores as gerais que aceitem o papel apenas em zitadel e rejeitem esse papel nos outros bancos. Sem essa prova, nao iniciar.

## Ordem apos autorizacao explicita

1. Registrar a-e na jornada; acesso SSH somente conforme autorizacao especifica do experimento. Confirmar clone, projeto, rede e ausÃªncia de recursos homonimos; nao sobrescrever banco/volume preexistente.
2. De `experiments/zitadel/`, executar `python -m experiments.tools.generate_env` com PYTHONPATH apontando a raiz. O script so roda no caminho autorizado, nao sobrescreve `.env`, cria 600 e nao imprime segredos. Chave mestra tem exatamente 32 caracteres. Preencher expiracao curta do PAT (ISO UTC), IDs e credenciais do cliente na VPS; nunca enviar valores ao chat/CI. Nao usar `compose config` sem `--quiet` com ambiente real.
3. Criar papel/banco via sessao local administrativa do Postgres, usando segredo do DSN por entrada padrao, sem linha de comando ou logs. Confirmar negacao de conexao do papel ao banco didasko e acesso ao zitadel. Isolamento nao comprovado = parar infra e registrar bloqueio.
4. Inicializar exclusivamente o volume novo (diretorio UID1000/GID1001, 2750); subir primeiro `identity-api`, depois conferir a geracao do PAT e permitir leitura apenas ao grupo 1001 (0640), e so entao subir `identity-login`, usando `sudo -n docker compose -p experimento-oidc up -d <servico>` no diretorio da config. Nao rodar compose do deploy.
5. No console do provedor: criar organizacao de teste, projeto, roles coordenador/instrutor, app Web OIDC code+PKCE e callback exato `https://homolog.didasko.app.br/experimento/callback`; ativar roles no ID token. Criar conta de servico com permissoes de criar usuarios/grants **so nessa organizacao**, emitir PAT curto. Nao usar IAM_OWNER no cliente. Registrar IDs sem tokens.
6. Preencher ORGANIZATION_ID, PROJECT_ID, CLIENT_ID/SECRET, ENVIRONMENT, PROVISIONING_TOKEN. ORGANIZATION_CLAIM=`urn:zitadel:iam:user:resourceowner:id`; ROLES_CLAIM=`urn:zitadel:iam:org:project:roles` (confirmar token real sem registra-lo). SCOPES=`urn:zitadel:iam:user:resourceowner urn:zitadel:iam:org:id:<ORG> urn:zitadel:iam:org:project:id:<PROJECT>:aud urn:zitadel:iam:org:projects:roles` (openid/profile adicionados pelo cliente). PROVISIONING_ORG_HEADER=`x-zitadel-orgid`.
7. Construir/subir somente `identity-app`. E-01: login do coordenador e /me; E-02: POST/instructors via app, depois login do instrutor; E-03: confirmar que o provedor exige nova senha antes de voltar ao callback. Evidencia so status/etapas/IDs anonimos, nunca cookies/tokens/senhas.
8. Medir recursos, OOM/restarts e latencia; registrar falhas, sem aumentar limites sem autorizacao. Encerrar conforme autorizacao e especifica, com listagem previa dos recursos exatos e comprovacao da origem do banco/volume. Nao executar DROP de banco preexistente ou fora do projeto.

## Medicao reproduzivel

Depois de aquecer o provedor com um login e aguardar 60s de repouso, colher ao menos 10 amostras. No clone, `python -m experiments.tools.collect_memory --phase idle --output /tmp/dem016-idle.jsonl --samples 10`. Durante login, repetir com `--phase login` em paralelo (60 amostras). Coletor filtra apenas o projeto; guarda bytes por container, provedor (API+Login) e total com app. MB decimal no relatorio, Docker MiB convertido. Limite nao e consumo: 512+256+128 MiB = 939,52 MB de teto agregado; E-04 compara consumo real do provedor a 1.000.000.000 bytes, nao esse teto. Registrar tambem didasko_postgres/host por leitura, para distinguir impacto compartilhado de RSS dos novos containers.

E-05: instalar Playwright/Chromium **no ambiente de medicao isolado**, nao nas dependencias runtime nem na v0. Executar `python -m experiments.tools.login_latency --public-url https://homolog.didasko.app.br/experimento --output /tmp/dem016-login.json --username-selector <seletor> --username-submit <seletor> --password-selector <seletor> --password-submit <seletor>`. Seletores devem ser confirmados na UI oficial da tag, nao sao inventados no codigo. Credenciais lidas com getpass, sem screenshot/trace. Cada tentativa usa contexto novo e prompt=login, cronometra navegaÃ§Ã£o inicial ate callback e /me, incluindo render/JS/submissoes automaticas, sem tempo humano de digitacao. Forca uma geracao Ollama e espera o primeiro fragmento antes do login; registra sobreposicao ate o fim. Se geracao acabar antes, E-05 fica NAO_TESTADO, nunca PASS. Rodar geracao somente apos autorizacao do uso de carga na homologacao; se Ollama compartilhado com producao nao puder ser ocupado sem impacto, registrar impossibilidade e nao gerar carga.

Unir o array `trials` do JSON e as linhas idle/login no array `memory` de um JSON de evidencia; `python -m experiments.tools.measure <arquivo>` calcula maximo em repouso, pico no login e p95 nearest-rank de exatamente 3 amostras (o pior valor). Qualquer amostra >5s falha. Sem medicao, nunca preencher com os dados sinteticos dos testes.

## Fontes oficiais consultadas

- https://github.com/zitadel/zitadel/releases/tag/v4.19.5
- https://zitadel.com/docs/self-hosting/manage/reverseproxy/reverse_proxy
- https://raw.githubusercontent.com/zitadel/zitadel/v4.19.5/cmd/defaults.yaml
- https://raw.githubusercontent.com/zitadel/zitadel/v4.19.5/proto/zitadel/user/v2/user_service.proto
- https://github.com/zitadel/zitadel/blob/v4.19.5/LICENSING.md
- https://github.com/zitadel/zitadel/blob/v4.19.5/apps/login/LICENSE

Arquitetura API+Login V2 e h2c confirmada. Config final adaptada ao proxy/Postgres existentes, nao copia a infraestrutura inteira do exemplo oficial. Licenca do nucleo AGPL-3.0-only; excecao MIT para apps/login. Servicos nao modificados, comunicacao OIDC/HTTP, nenhum codigo do provedor incorporado ao Didasko. Interpretacao tecnica: a separacao evita criar obra derivada por incorporar o nucleo; nao representa dispensa geral das obrigacoes AGPL. Se houver modificacao do nucleo oferecida pela rede, oferecer fonte correspondente conforme secao 13; distribuicao de imagens exige preservar avisos/licenca e cumprir oferta de fonte aplicavel. MIT permite uso/modificacao/distribuicao preservando aviso e licenca. Decisao juridica/adocao e do ARQUITECT.
