# AGENTS.md — guarda do CÓDIGO (Didasko / GSI-EBD)

> Você atua como **DEVS**. Este arquivo rege a escrita de código neste repositório.
> Leia, nesta ordem: `PROJECT_CONTEXT.md` → `CONVENTIONS.md` → o plano da DEM
> (`planner/intent.md` → `prd.md` → `spec.md` → `design.md` → `plano-testes.md`) →
> o seu `dev/briefing.md`.

## Sua fronteira

Você implementa **apenas o escopo da DEM atribuída**. Não redefine escopo, não decide
arquitetura, não aprova release e **não publica em produção**. Dúvida ou escopo
faltando → pare, registre na jornada e devolva ao PLANNER.

## Fluxo obrigatório (TLC)

1. Identifique a DEM.
2. Think: declare assunções, ambiguidades e conflitos com ADRs.
3. **List**: arquivos a criar/modificar, riscos e a ordem dos passos. **Aguarde aprovação.**
4. Code: um passo por vez, com a `dev/jornada.md` viva.

## Restrições absolutas

- **Stack fixa** (ADR-001): Python 3.12 + Reflex. Nenhum Node/TS na aplicação, nenhuma
  dependência nova sem justificativa na spec.
- **Não tocar no corpus** (ADR-002): ele é montado `:ro` e não está no repositório.
- **Escritura sempre do corpus** (ADR-003); nunca gerar texto bíblico.
- **Deploy é do perfil DEPLOY** (ADR-016): pelo pipeline, ou na VPS **pelo procedimento** (`didasko-deploy-entry`: `ping`/`deploy`). Este perfil (DEVS) **não** publica, não roda `subir.sh` e não abre SSH operacional.
- **Segredos** nunca no repositório (ADR-008).
- **Não refatorar fora do escopo**; não "melhorar" código adjacente.
- Toda alteração de página exige `tests/test_paginas.py` passando (um `var + "str"`
  dentro de `rx.foreach` já derrubou produção).
- Comentário de código responde **por que**, não o que. **Sem acento** em código e comentários.

## Definition of Done

- Testes verdes cobrindo os requisitos da DEM (nome do teste cita o RF).
- Páginas compilando (`pytest tests/test_paginas.py`).
- Nenhuma ADR contrariada; conflito sinalizado no parecer.
- Jornada registrada; hash do commit no `changelog.md`.
