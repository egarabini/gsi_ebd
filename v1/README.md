# Didasko v1 — esqueleto local e fluxo de obras

Esta pasta implementa as etapas A e B da DEM-202610-011, fatia 2. Não muda o banco da v0 nem contém deploy, imagem, DNS ou homologação.

## Rodar localmente (PowerShell)

Na raiz do app, instale `python -m pip install -r requirements-dev.txt -r v1/requirements.txt`. Entre em `v1/` e configure o ambiente (ou um `.env` local, que não entra no Git):

```powershell
$env:DATABASE_URL = "sqlite:///./didasko_v1.db"
$env:COOKIE_SECURE = "false"
$env:SESSION_SECRET = (& ..\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
# Aponte para o inventário real, fora do app:
$env:CAMINHO_INVENTARIO = "C:\Projetos\EM_ESTUDO\EVANGELICOS\documentacao\fontes\inventario.csv"
$env:PYTHONPATH = ".."
..\.venv\Scripts\python.exe -m v1.criar_usuario admin@example.test --papel ADMIN
..\.venv\Scripts\python.exe -m v1.criar_usuario revisor@example.test --papel REVISOR
..\.venv\Scripts\python.exe -m uvicorn v1.main:create_app --factory --app-dir .. --host 127.0.0.1 --port 8001
```

Abra `http://127.0.0.1:8001/login`. O bootstrap pede a senha sem exibi-la, não redefine contas existentes e exige troca no primeiro login. Não há senha fixa, seed automático ou criação de usuário no boot.

SQLite é opção local descartável; PostgreSQL deve apontar explicitamente para `didasko_v1`. `create_all` no boot cria tabelas ausentes, sem executar migração ou alterar colunas de tabelas existentes. O baseline e a provisão do banco de produção são da DEM-005.

## Sessão e autenticação

O cookie `didasko_v1` contém apenas um identificador opaco assinado pelo SessionMiddleware; usuário, CSRF e expiração ficam na memória do processo. Sessões são independentes da v0; rotação no login/troca, revogação no logout e prazo de uma hora. Esta etapa local usa **um processo**: reiniciar invalida sessões; persistência compartilhada/múltiplos workers ficam para a implantação da v1. `COOKIE_SECURE` é true por padrão, false apenas no HTTP local; HttpOnly e SameSite=Lax sempre ativos.

`SESSION_SECRET` é obrigatório, sem fallback. A senha usa o bcrypt existente; o papel e a flag são lidos do banco a cada request, nunca do formulário/cookie. AuthService e metadados de sucesso do UserStatusService são reaproveitados. A troca local verifica a senha atual, impede reutilização, limpa a flag e revoga as demais sessões; não dispara email ou fluxo de reativação, fora desta etapa.

CSRF em todo POST, inclusive login/logout: campo `csrf_token` ou `X-CSRF-Token` no HTMX. O H-14 recusa com 403 qualquer rota da app para usuário com troca pendente, exceto perfil e logout. Assets estáticos não carregam dados de usuário.

## Fluxo

Admin: `/admin/obras`. Revisor: `/revisor/obras`. Detalhe compartilhado: `/obras/{id}`, restrito aos papéis de leitura do catálogo (Admin/Revisor). Coordenador, instrutor e aluno podem trocar senha/sair, mas não têm telas nesta fatia.

As três permissões específicas foram acrescentadas a `gsi_ebd/utils/rbac.py`, sem mudar as permissões da v0. Todos os handlers protegidos usam a matriz como dependência do servidor.

A importação recebe o ID de fonte do inventário e conteúdo digitado; não lê nem redistribui corpus. Formulários de capítulos/adendos da **base** são adaptados para os modelos existentes. Ajustes dentro do ciclo são aplicados na mesma transação da liberação/reenvio; recusa reverte tudo. Nova versão/aceite/suspensão/liberação/dispensa/cancelamento/parecer/posição são decididos pelo `flow.py`. Nenhum modelo ou campo do domínio foi alterado.

A rota adicional `/admin/obras/{id}/reenviar` completa a transição já existente de recusa/reenvio. Conteúdo publicado e cópia de trabalho são exibidos separadamente; o histórico inclui hashes e motivos de dispensa. Markdown aparece escapado como texto para revisão, sem executar HTML. Não há desvinculação, adendo de ambiente ou planejamento.

## Testes

Execute a suíte desta pasta **a partir de `v1/`**:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
```

Regressão da fatia 1: na raiz do app, `python -m pytest tests -q`. O CI executa as duas suítes nos respectivos diretórios. O Jinja usa StrictUndefined; a matriz cobre cinco papéis e todas as rotas, CSRF/H-14 e fluxo HTTP real com banco descartável. Nenhum segredo ou corpus é necessário nos testes.

HTMX 2.0.4 é servido localmente, com sua licença (`static/htmx.LICENSE`); os formulários funcionam também sem JavaScript. Alpine não foi adicionado porque não há comportamento que o exija nesta fatia. Fontes técnicas: [templates do FastAPI](https://fastapi.tiangolo.com/advanced/templates/) e [HTMX](https://github.com/bigskysoftware/htmx/tree/v2.0.4).

Provas reproduzíveis, de `v1/`: `python tools/mutacoes.py --evidencias <pasta-nova>`. Cada seletor roda antes/depois em uma cópia fora do repositório; os originais ficam intactos.
