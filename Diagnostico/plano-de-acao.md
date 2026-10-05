# Plano de Acao

## Objetivo

Preparar o `GSI_EBD` para receber voz com MCP de forma sustentável, sem perder a estabilidade do fluxo atual.

## Fase 1 - Estabilizacao da Base

### 1. Revisar e padronizar o dominio

- Consolidar os modelos de estudo e progresso.
- Definir formato estável para `questions_json`.
- Validar campos obrigatórios dos seeds.

### 2. Centralizar regras de negocio

- Criar camada de serviços para estudo, progresso e autorização.
- Reduzir o peso de `states` como lugar de regra de domínio.

### 3. Fechar o RBAC

- Implementar checks centrais por role.
- Garantir que cada página respeite seu papel.
- Tornar o coordenador funcional.

## Fase 2 - Preparacao para Voz

### 4. Criar contrato MCP

- Definir tools para leitura de estudo, contexto bíblico, log de voz e resumo.
- Separar tool de orquestração de tool de domínio.

### 5. Criar telemetria mínima

- Registrar respostas.
- Registrar tempo gasto.
- Registrar eventos de voz quando existirem.

### 6. Estruturar IA como serviço reutilizável

- Unificar entrada de texto para estudo e voz.
- Garantir respostas curtas e pedagógicas.

## Fase 3 - POC de Voz

### 7. Adicionar interação por voz na tela da lição

- botão para gravar áudio
- STT para transcrição
- resposta em texto e áudio

### 8. Integrar com o fluxo do aluno

- usar o mesmo contexto da lição aberta
- permitir repetir pergunta e ouvir explicação
- registrar tentativa no progresso

## Ordem Recomendada de Execucao

1. padronizar modelos e seed
2. criar camada de serviços
3. fechar RBAC
4. documentar contrato MCP
5. implementar logging e telemetria
6. fazer POC de voz

## Entregavel Imediato Sugerido

O próximo entregável técnico deve ser um pacote de arquitetura com:

- `services/study_service.py`
- `services/progress_service.py`
- `services/auth_service.py`
- `mcp/` ou `voice/` com contrato inicial
- atualização dos estados para usar serviços
