# Arquitetura Atual

## Estrutura Observada

- `gsi_ebd.py`: registra rotas e integra estados/páginas.
- `rxconfig.py`: configuração do app e banco.
- `models/`: `User`, `Study`, `StudyVersion`, `StudyAssignment`, `UserResponse`, `Progress`.
- `states/`: autenticação, administração, gestão de alunos e fluxo do aluno.
- `pages/`: login, admin, gestor, aluno e lição.
- `services/`: pontos de extensão para IA e Bíblia.
- `ai/`: espaço para agentes.
- `data/seed.py`: carga inicial.
- `tests/test_models.py`: validações mínimas de modelo.

## Fluxo Principal

1. Usuário faz login.
2. `AuthState` define role e redireciona.
3. Admin cadastra supervisores e gestores.
4. Gestor cadastra alunos e atribui estudos.
5. Aluno visualiza estudos atribuídos.
6. Lição é aberta, respondida e salva em `UserResponse`.
7. Ao concluir, `Progress` é gravado.

## Forças da Estrutura

- Separação razoável de responsabilidades por pasta.
- Modelo de papéis já preparado para hierarquia.
- Fluxo de estudo já persistente.
- Base boa para POC rápida.

## Fragilidades Estruturais

- Falta camada de serviço para regras de negócio.
- Estados concentram acesso ao banco e decisões de domínio.
- Supervisor ainda não está funcional.
- Não há contrato forte para conteúdo de lição.
- Não há telemetria de uso nem logging de interações.

## Implicacao Para Voz

A voz deve entrar como nova camada sobre `services/` e `ai/`, com uma interface de tools MCP, e não como lógica direto nas páginas.
