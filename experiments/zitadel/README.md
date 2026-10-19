# DEM-016: experimento isolado de identidade

**Nao adotado. Infraestrutura autorizada com condicoes em 19/10.** Inicio depende da credencial Basic Auth do ARQUITECT; desmonte exige confirmacao na hora. Nao altera v0, v1, RF01 ou flow.py.

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

## Configuracao autorizada em 19/10, com condicoes

O codigo esta pronto; o veredito depende da homologacao. Nenhuma recomendacao antes das medidas reais. O workflow experiment.yml e temporario e sai junto com o experimento.

- Clone `/home/didasko-deploy/experimentos/didasko/`; projeto obrigatorio `experimento-oidc`.
- Postgres **dedicado**, `postgres:16`, banco/papel zitadel, volume `experimento-oidc_database`, somente rede `internal` marcada `internal: true`, sem portas publicadas. **Nunca conectar ao didasko_postgres**, sem HBA/ACL/DROP no banco existente. Esta decisao substitui integralmente a proposta anterior de banco compartilhado.
- API v4.19.5: teto `1g`; Login V2 v4.19.5: `256m`; cliente FastAPI: `128m`. Postgres integra a medicao real e aparece discriminado. Teto nao representa consumo nem resultado de E-04.
- API+Login+app estao na rede interna e na `deploy_didasko` por serem roteados. Postgres nunca entra na rede do Traefik. Nenhum servico adicional ou volume da v0.
- API em h2c:8080 no host `oidc.homolog.didasko.app.br`; Login V2 HTTP:3000 no mesmo host com prioridade maior em `/ui/v2/login`; app:8000 em `Host(homolog.didasko.app.br) && PathPrefix(/experimento)`. TLS websecure/le, httpchallenge existente. Nenhuma mudanca global no Traefik.
- A app exige middleware Basic Auth antes do strip-prefix; htpasswd vem exclusivamente do ARQUITECT em `EXPERIMENT_BASIC_AUTH_USERS`. A configuracao falha se ausente. `removeheader=true` evita encaminhar a credencial para a app. Nunca imprimir `compose config` interpolado ou `docker inspect` integral.
- UID API1000:1000, Login1001:1001. Bootstrap nomeado proprio: diretorio UID1000/GID1001 modo 2750; depois da API gerar PAT, somente esse arquivo recebe UID1000/GID1001 modo0640, antes de iniciar o Login. Nenhum processo root permanente; nenhuma permissao alterada fora desse volume novo. Se algo divergir, parar e devolver ao PLANNER.
- Digests publicos consultados: API sha256:a586456a208e0db4c633db0ba43c427c24b37846138b8b13ff16ad8e003a18d3; Login sha256:2f8e57672fcd4f9a285d99355fae9f85fd7495768c090c07c3bbc2d84fc06617. Revalidar antes de executar a tag; divergencia nao autoriza atualizar silenciosamente.

## Ordem operacional, apos receber a credencial e confirmar acesso

1. Obter do ARQUITECT por canal seguro o htpasswd e a credencial de navegador. Pedir somente o caminho de arquivo 600 na VPS pelo chat, nunca o conteudo. Nao inventar credenciais Basic Auth. Alias SSH autorizado: didasko-vps, usuario didasko-deploy, sudo -n docker. Nenhum recurso esperado ausente autoriza contorno.
2. Confirmar clone isolado, branch/commit, ausencia de recursos homonimos e rede autorizada. Arquivo `.env` no diretorio da config, 600, dono didasko-deploy. Gerador `experiments.tools.generate_env` usa openssl rand por subprocess, captura diretamente para arquivo exclusivo, nao sobrescreve nem imprime valores. Chave mestra exatamente 32 caracteres. Admin permanece no .env; ARQUITECT le pela propria sessao na VPS.
3. Preencher expiracao curta do PAT e htpasswd no .env por canal protegido. Criar somente os volumes do projeto, preparar bootstrap como descrito. `sudo -n docker compose -p experimento-oidc up -d identity-db identity-api`; confirmar health e permissao do PAT, depois iniciar identity-login. App e iniciada so apos configuracao OIDC. Nao executar compose do deploy existente.
4. Criar org/projeto de teste, roles coordenador/instrutor e app Web OIDC code+PKCE no provedor; callback exato `https://homolog.didasko.app.br/experimento/callback`. Roles no ID token; conta de servico com permissoes de criar usuarios/grants somente na org. Configurar IDs/secret/PAT no .env, sem imprimir. Email sintetico verificado neste ensaio, sem SMTP.
5. Claims/scopes: ORGANIZATION_CLAIM=`urn:zitadel:iam:user:resourceowner:id`; ROLES_CLAIM=`urn:zitadel:iam:org:project:roles` (confirmar no token real sem registra-lo). SCOPES=`urn:zitadel:iam:user:resourceowner urn:zitadel:iam:org:id:<ORG> urn:zitadel:iam:org:project:id:<PROJECT>:aud urn:zitadel:iam:org:projects:roles`; PROVISIONING_ORG_HEADER=`x-zitadel-orgid`. openid/profile adicionados pelo cliente. DSN aponta somente a identity-db.
6. Subir identity-app. E-01: login coordenador e /me com papel/ambiente. E-02: POST/instructors pela app e login do instrutor criado. E-03: observar troca obrigatoria na UI do provedor antes do callback; a app nao implementa essa troca. Registrar etapas/status anonimos, sem screenshots/tokens/senhas.
7. E-04/E-05 abaixo. Qualquer divergencia de infraestrutura exige parar e devolver ao PLANNER; nao ampliar limites ou redes silenciosamente.

## Medicao real

E-04: aquecer com um login, aguardar 60s e coletar >=10 amostras de repouso, e amostrar durante logins. `python -m experiments.tools.collect_memory --phase idle --output /tmp/dem016-idle.jsonl --samples 10`; repetir em paralelo ao login com --phase login e intervalo suficiente. Coletor filtra o projeto, exige os quatro servicos e guarda bytes individuais, conjunto do provedor (API+Login+Postgres) e total com app. Converter bytes para MB decimais; registrar repouso e pico no login, alem de OOM/restarts. Criterio em repouso: provedor <1.000.000.000 bytes. Sem excluir Postgres para melhorar o numero.

E-05: **>=10 logins**, **mediana <=2s** e **maximo <=5s**, todos com geracao Ollama em andamento. Instalacao de Playwright/Chromium apenas no ambiente de medicao, nao na v0. Ferramenta:

`python -m experiments.tools.login_latency --public-url https://homolog.didasko.app.br/experimento --trials 10 --credentials-file <arquivo-600-na-VPS> --output /tmp/dem016-login.json --username-selector <seletor> --username-submit <seletor> --password-selector <seletor> --password-submit <seletor>`

Arquivo privado JSON com username/password do usuario ja com senha alterada e basic_username/basic_password fornecidos pelo ARQUITECT. Nao versionar nem enviar seu conteudo; opcionalmente a ferramenta le por getpass em sessao humana. Seletores confirmados na UI oficial. Basic Auth do navegador limitada a origem da app, sem envia-la ao host do provedor. Cada tentativa usa contexto novo e prompt=login; verifica subject/role/environment antes de aceitar a medida. Cronometra desde navegacao inicial ate /me com identidade, incluindo redirects, render e submissoes automaticas; sem tempo humano de digitacao. Espera primeiro fragmento da geracao e verifica que continuou ate o fim. Gera 10 medidas; ausencia de sobreposicao impede PASS. Nao executar carga se a infraestrutura divergir da autorizada; parar e devolver ao PLANNER.

Unir `trials` do JSON e linhas de memoria em array `memory`; `python -m experiments.tools.measure <arquivo>` calcula mediana/maximo, maximo em repouso e pico no login. Dados sinteticos dos testes nao viram evidencia real.

## Desmonte: NAO executar sem confirmacao na hora

Antes de pedir confirmacao, listar containers e volumes com filtro `com.docker.compose.project=experimento-oidc`, conferir a origem e listar o comando exato:

```bash
cd /home/didasko-deploy/experimentos/didasko/experiments/zitadel
sudo -n docker compose -p experimento-oidc -f docker-compose.yml down -v
```

Esse comando e um plano, nao uma autorizacao de execucao neste momento. Nao ha DROP no Postgres compartilhado, nem remocao automatica do clone ou de outro projeto. O workflow temporario e os arquivos do experimento serao removidos por revisao no fim, preservando o relatorio/evidencias.

## Fontes oficiais consultadas

- https://github.com/zitadel/zitadel/releases/tag/v4.19.5
- https://zitadel.com/docs/self-hosting/manage/reverseproxy/reverse_proxy
- https://raw.githubusercontent.com/zitadel/zitadel/v4.19.5/cmd/defaults.yaml
- https://raw.githubusercontent.com/zitadel/zitadel/v4.19.5/proto/zitadel/user/v2/user_service.proto
- https://github.com/zitadel/zitadel/blob/v4.19.5/LICENSING.md
- https://github.com/zitadel/zitadel/blob/v4.19.5/apps/login/LICENSE

Arquitetura API+Login V2 e h2c confirmada. Config final adaptada ao proxy/Postgres existentes, nao copia a infraestrutura inteira do exemplo oficial. Licenca do nucleo AGPL-3.0-only; excecao MIT para apps/login. Servicos nao modificados, comunicacao OIDC/HTTP, nenhum codigo do provedor incorporado ao Didasko. Interpretacao tecnica: a separacao evita criar obra derivada por incorporar o nucleo; nao representa dispensa geral das obrigacoes AGPL. Se houver modificacao do nucleo oferecida pela rede, oferecer fonte correspondente conforme secao 13; distribuicao de imagens exige preservar avisos/licenca e cumprir oferta de fonte aplicavel. MIT permite uso/modificacao/distribuicao preservando aviso e licenca. Decisao juridica/adocao e do ARQUITECT.
