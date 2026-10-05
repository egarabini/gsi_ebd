# Plano de Acao - Hierarquia, Equipes e Modulo Coordenador

## Objetivo

Fechar a lacuna entre o fundamento de negocio (4 niveis de acesso x 5 modulos) e o codigo atual do `GSI_EBD`, a partir do diagnostico em `avaliacao-fundamento-plataforma.md`. Cobre: correcao de hierarquia (concluida), modelagem de Turma/Equipe, modulo de Coordenacao de Alunos e fluxo de proposta/aprovacao de planos de estudo.

## Fase 0 - Correcao de Hierarquia (CONCLUIDA nesta rodada)

- [x] `Role` reordenado para `ADMIN=1, GESTOR=2, COORDENADOR=3, ALUNO=4`.
- [x] Renomeacao completa `Coordenador` -> `Coordenador` em models, states, pages, components, services, utils, seed e testes.
- [x] `User.coordenador_id` -> `User.coordenador_id`; `meta_coordenadores` -> `meta_coordenadores`.
- [x] Corrigido bug pre-existente `User(nome=...)` -> `User(nome_completo=...)` em `states/admin.py`, `states/gestor.py`, `states/auth.py`, e usos de leitura em `pages/admin.py`, `pages/gestor.py`, `states/auth.py` (o model usa `nome_completo`/`nome_base`, nao `nome`).
- [x] Suite de testes (`pytest`) validada: 5 passed.
- Pendente (nao critico agora): atualizar referencias textuais a "Coordenador" em `README.md`, `plano-de-acao.md`, `arquitetura-atual.md`, `MCP-VOICE-FRAMEWORK.md`, `Evolução.md` (apenas documentacao).
- Observacao tecnica: nao existe migracao Alembic a ser feita para o rename de coluna, pois o banco e criado via `SQLModel.metadata.create_all()` em `data/seed.py` (unica migracao existente, `b55ed43e2631_.py`, esta desatualizada em relacao ao model atual). Recomenda-se, em fase futura, regenerar as migracoes Alembic a partir do model corrente antes de ir para producao com dados reais.

## Fase 1 - Entidade Turma/Equipe [CONCLUIDA]

Hoje o vinculo Gestor->Coordenador->Aluno e feito so por FK direta em `User` (`gestor_id`, `coordenador_id`), sem conceito de Turma. Isso limita: um Coordenador so pode ter 1 conjunto fixo de alunos, sem historico, sem data de inicio/fim, sem multiplos planos simultaneos.

**Status:** implementado. `models/turma.py` criado (`Turma`, `TurmaMembro`), registrado em `models/__init__.py`. `create_coordenador` (`states/admin.py`) agora exige selecionar um Gestor (`gestor_options`, `new_coordenador_gestor_id`) e a UI (`pages/admin.py`) tem o seletor correspondente. `data/seed.py` cria uma Turma de exemplo com 2 alunos via `seed_turmas()`. Migracao Alembic `95d76c5dbb2f_turma_turmamembro.py` (down_revision `b55ed43e2631`) criada e validada manualmente contra SQLite limpo (`alembic upgrade head` ok, colunas confirmadas). Suite de testes (`pytest tests/`) permanece 100% verde.

### 1. Criar model `Turma` (`models/turma.py`)

- `id`, `nome`, `descricao`
- `gestor_id` (FK user) — dono da turma
- `coordenador_id` (FK user, opcional) — responsavel operacional
- `study_id` (FK study, opcional) — plano de estudo associado
- `data_inicio`, `data_fim` (opcional)
- `is_active`
- `created_at`

### 2. Criar tabela associativa `TurmaMembro`

- `turma_id`, `user_id` (aluno), `data_entrada`, `data_saida` (opcional)
- Permite um aluno participar de mais de uma turma ao longo do tempo (historico preservado).

### 3. Migrar logica de hoje

- Manter `coordenador_id` em `User` como vinculo "primario" (compatibilidade), mas passar a tratar `Turma` como fonte de verdade para relatorios/dashboards.
- Ajustar `create_coordenador` (`states/admin.py`) para exigir `gestor_id` no momento da criacao (hoje o Coordenador e criado sem vinculo a nenhum Gestor).

## Fase 2 - Modulo Coordenacao de Alunos

Hoje so existe um placeholder de rota `/coordenador` ("Em breve"). Nada implementado.

### 4. `states/coordenador.py`

- `CoordenadorState(rx.State)` com: `alunos` (lista dos alunos da(s) turma(s) do coordenador), `turmas`, metricas agregadas (media de progresso, assiduidade, pendencias).
- Metodos: `load_turmas()`, `load_alunos()`, `atribuir_estudo(aluno_id, study_id)`, `remover_aluno(aluno_id)`.

### 5. `pages/coordenador.py`

- Dashboard com cards de turma, lista de alunos com progresso (reaproveitar padrao visual de `_aluno_card` em `pages/gestor.py`).
- Tela de atribuicao de estudo por aluno/turma (usa `StudyAssignment` já existente em `models/study.py`).
- Tela de acompanhamento de respostas/dificuldades (usa `Progress`/`UserResponse`).

### 6. Rotas e RBAC

- Registrar `/coordenador` como pagina real em `gsi_ebd.py` (remover placeholder).
- Sidebar (`components/sidebar.py`) ja aponta para `/coordenador` — apenas validar após criar a pagina.
- Reforcar `rbac.py` para restringir Coordenador a ver somente alunos das suas turmas (usar `can_manage` + filtro por `turma`).

## Fase 3 - Fluxo de Proposta e Aprovacao de Planos de Estudo

`models/study.py` ja tem `StudyStatus` (pipeline editorial) mas o fluxo Gestor-propoe / Admin-aprova nao esta implementado em states/pages.

### 7. Completar pipeline editorial

- `states/gestor.py`: `propor_estudo()` cria `Study` com status `PROPOSTO` (ou equivalente existente em `StudyStatus`).
- `states/admin.py`: `aprovar_estudo(study_id)` / `rejeitar_estudo(study_id, motivo)`.
- Disparar `Notification` (`ESTUDO_PROPOSTO`, `ESTUDO_APROVADO`, `ESTUDO_REJEITADO` — ja existem no enum de `models/notification.py`).

### 8. UI de aprovacao no Admin

- Nova aba em `pages/admin.py` listando estudos pendentes de aprovacao, com acoes aprovar/rejeitar.

## Fase 4 - Modulo Administrativo/Financeiro (fora do escopo imediato)

- Hoje opera em `PaymentMethod.SIMULADO`. Sair do modo simulado (gateway real) e tema de fase posterior, nao tratado neste plano.

## Ordem Recomendada de Execucao

1. Fase 0 (concluida).
2. Model `Turma` + `TurmaMembro` + migracao/seed de exemplo.
3. Ajustar criacao de Coordenador para exigir `gestor_id`.
4. `states/coordenador.py` + `pages/coordenador.py` (MVP: listar alunos e atribuir estudo).
5. Pipeline de proposta/aprovacao de estudos (Fase 3).
6. Revisao de RBAC fino por turma.
7. Atualizacao dos documentos de diagnostico/arquitetura para refletir o estado novo.

## Riscos e Pontos de Atencao

- `Turma` adiciona uma tabela nova — exige nova migracao Alembic real (diferente da correcao atual, que nao precisou de migracao por falta de dados em producao).
- Sem `Turma`, o modulo de Coordenacao pode ser entregue de forma simplificada (direto via `coordenador_id` em `User`), mas isso adia dividas tecnicas que crescem com o numero de turmas por coordenador.
- Recomenda-se decidir com o usuario se o MVP do modulo Coordenador entra **sem** `Turma` (mais rapido, usa `coordenador_id` direto) ou **com** `Turma` (mais robusto, maior esforco inicial).
