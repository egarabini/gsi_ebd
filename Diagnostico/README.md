# Diagnostico do GSI_EBD

Data de revisao: 2026-07-14

## Resumo Executivo

O `GSI_EBD` já possui a espinha dorsal do produto: autenticação por email e senha, perfis de acesso, cadastro de gestores e alunos, atribuição de estudos, execução de lições, registro de respostas e persistência de progresso.

O estado atual é de um MVP funcional em estrutura, mas ainda com pontos importantes de maturidade antes da próxima fase. O principal deles é a consolidação da arquitetura para suportar voz via MCP sem acoplar cedo demais a interface, o estado e as regras de domínio.

## O Que Ja Existe

- App Reflex com rotas por perfil.
- Login, registro e redirecionamento por role.
- RBAC básico com `ADMIN`, `SUPERVISOR`, `GESTOR` e `ALUNO`.
- Cadastro de gestores e alunos pelo painel administrativo e do gestor.
- Modelo de estudos com `Study`, `StudyVersion` e `StudyAssignment`.
- Modelo de progresso com `UserResponse` e `Progress`.
- Fluxo de lição com perguntas, correção local e persistência das respostas.
- Seed inicial para admin e lições JSON.

## Principais Achados

### 1. Arquitetura geral está coerente, mas ainda pouco modular

O app já separa `models`, `states`, `pages`, `components`, `services` e `ai`. Isso é bom. O problema é que a maior parte da regra de negócio ainda está espalhada em `states`, com pouca camada de serviço intermediária.

Impacto:

- dificuldade para evoluir o domínio sem mexer na UI
- maior risco de duplicação de lógica
- mais difícil encaixar MCP, voz e agentes de forma limpa

### 2. O fluxo de estudo já funciona, mas ainda é simples demais para a visão do produto

O `AlunoState` já carrega estudo, controla questões e grava respostas, mas a experiência ainda é linear e pouco adaptativa.

Lacunas:

- não há leitura guiada, áudio ou apoio multimodal
- não há adaptação real baseada em histórico
- não há resumos de dificuldades por tópico
- o feedback de IA ainda não está integrado ao loop principal

### 3. RBAC existe, mas está incompleto no nível de enforcement

As roles estão modeladas, porém a proteção de acesso ainda é majoritariamente implícita via páginas e checks simples.

Pontos a observar:

- `check_auth` protege login, mas não há uma política centralizada por role
- supervisor está previsto na rota, mas ainda não tem painel real
- há pouca validação de contexto ao usar `current_user_id` em queries

### 4. Persistência e seed existem, mas faltam contratos mais explícitos

O seed cria admin e estudos, mas o formato dos JSONs e o contrato de `questions_json` ainda estão muito livres.

Riscos:

- inconsistência entre lições diferentes
- dificuldade de validar conteúdo antes de persistir
- maior custo para integrar voz e leitura de conteúdo estruturado

### 5. A base já aponta para IA, mas ainda sem uma integração operacional clara

Os arquivos de `services/ai_service.py` e `ai/agents.py` existem, mas a solução ainda não está visivelmente consolidada como pipeline.

Isso afeta diretamente a futura voz, porque voz deve acionar o mesmo núcleo de inteligência que texto usa.

### 6. A documentação de visão é boa, mas agora precisa virar contrato de execução

Os documentos `Visão.md`, `Evolução.md` e `MCP-VOICE-FRAMEWORK.md` são úteis como direção, mas o próximo salto é transformar isso em backlog técnico e decisões concretas de arquitetura.

## Riscos Prioritarios

- Misturar o fluxo de voz diretamente nas páginas antes de definir os serviços.
- Continuar armazenando lógica de domínio em `states` sem uma camada de serviço.
- Crescer o sistema sem padronizar o formato das lições e respostas.
- Não definir logging e auditoria desde o início para interações por voz.
- Deixar o supervisor como papel “decorativo” sem uso real.

## Conclusao Tecnica

O projeto está em um ponto bom para avançar, mas a próxima fase precisa priorizar estabilização estrutural antes de adicionar voz.

Atualização de progresso:

- camada de serviços de estudo e progresso criada
- RBAC começando a sair do estado implícito para helpers reutilizáveis
- base melhor preparada para o contrato MCP de voz

Se a voz for implementada agora sem esse ajuste, o risco é criar um POC difícil de manter. Se fizermos a preparação certa, a voz entra como uma evolução natural do estudo guiado.

## Documentos Relacionados

- `Diagnostico/arquitetura-atual.md`
- `Diagnostico/plano-de-acao.md`
