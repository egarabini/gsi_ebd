# MCP Voice Framework para GSI_EBD

## Objetivo

Documentar a estratégia para adicionar voz ao `GSI_EBD` sem alterar a base atual de forma prematura. A voz deve ser tratada como uma camada de interação sobre a arquitetura existente, não como substituição da navegação principal.

## Direção

O sistema atual já aponta para:

- autenticação com papéis (`ADMIN`, `COORDENADOR`, `GESTOR`, `ALUNO`)
- estudos dirigidos com progresso e trilha de aprendizado
- serviços de IA para explicação, apoio pedagógico e adaptação

A próxima evolução natural é permitir que o aluno interaja por voz com as lições, com o tutor e com o assistente de estudo, mantendo rastreabilidade, contexto e segurança.

## Princípios de implementação

- Voz deve ser opcional e incremental.
- O fluxo principal continua funcionando por texto e interface visual.
- Todo uso de voz precisa respeitar RBAC e contexto do usuário logado.
- A experiência de voz deve servir o estudo bíblico, não distrair dele.
- O componente de voz deve reutilizar os mesmos serviços de estudo, progresso e IA.

## Arquitetura-alvo

### Camadas

1. Interface web em Reflex
2. Camada de orquestração de voz via MCP
3. Serviços de STT, TTS e agente conversacional
4. Serviços existentes de estudo, Bíblia, progresso e IA

### Fluxo sugerido

1. O usuário fala uma pergunta ou comando.
2. O áudio é convertido em texto por STT.
3. O texto entra no planner/agente.
4. O planner decide se chama:
   - busca em estudo
   - leitura bíblica
   - resumo contextual
   - registro de progresso
   - resposta pedagógica
5. A resposta textual é convertida em áudio por TTS.
6. A interface registra o evento para auditoria e evolução pedagógica.

## Casos de uso prioritários

- Ler um trecho do estudo em voz alta.
- Fazer perguntas ao assistente sobre a lição atual.
- Solicitar explicação simples de um conceito bíblico.
- Repetir uma pergunta e ouvir a resposta novamente.
- Marcar dificuldade em uma questão por comando de voz.
- Ajudar o tutor com resumos de aluno em formato falado ou text-to-speech.

## O que o MCP deve oferecer

O MCP deve expor ferramentas claras, pequenas e observáveis. Exemplos:

- `get_current_study`
- `search_study_context`
- `read_bible_reference`
- `summarize_lesson`
- `log_voice_interaction`
- `record_answer_attempt`
- `generate_tutor_summary`

Essas tools não devem conter regra de negócio complexa. Elas devem orquestrar serviços já existentes.

## Componentes a prever

### 1. STT

Responsável por transformar fala em texto.

Critérios:

- baixa latência
- boa acurácia em português
- suporte a uso web/mobile

### 2. TTS

Responsável por sintetizar a resposta.

Critérios:

- voz natural em português
- suporte a frases bíblicas e leitura pausada
- controle de velocidade e destaque de versículos

### 3. Planner/Agent

Responsável por decidir a intenção e chamar as tools corretas.

Esse agente deve ser conservador, porque o domínio é teológico e pedagógico.

### 4. Logger de interação

Responsável por registrar:

- texto reconhecido
- intenção detectada
- tools chamadas
- resposta final
- tempo de resposta
- falhas de reconhecimento

## Ajustes necessários no GSI_EBD

Antes de implementar voz, a base deve estar mais clara em alguns pontos:

- consolidar modelos de estudo, versão e atribuição
- fechar o contrato de `states` por role
- padronizar serviços de IA e Bíblia
- definir onde o histórico de interação é persistido
- separar bem UI, estado e serviço

## Fase 1 recomendada

Objetivo: preparar o terreno.

- revisar a estrutura do estudo atual
- documentar o fluxo de lição e progresso
- definir eventos que serão auditados pela voz
- criar um contrato inicial do MCP

## Fase 2 recomendada

Objetivo: prova de conceito.

- botão de falar dentro da tela da lição
- transcrição para texto
- agente responde com texto e áudio
- log da interação no banco

## Fase 3 recomendada

Objetivo: integração pedagógica.

- leitura guiada da lição
- perguntas por comando de voz
- feedback adaptativo
- suporte ao tutor

## Riscos

- acoplamento precoce entre UI e voz
- latência alta prejudicando a experiência
- respostas longas demais para o modo falado
- risco de respostas fora da doutrina esperada se o prompt não tiver guarda-rails

## Decisão de produto

Voz não é um extra cosmético. Ela deve ser desenhada como um modo de estudo assistido, útil para:

- acessibilidade
- retenção de conteúdo
- uso em mobile
- apoio ao tutor e ao aluno

## Próximo passo prático

Depois de revisar a base atual, o próximo artefato a produzir deve ser:

1. um mapa dos fluxos atuais do `GSI_EBD`
2. um contrato de eventos para estudo e voz
3. um primeiro desenho das tools MCP
4. um POC pequeno de voz na tela da lição
