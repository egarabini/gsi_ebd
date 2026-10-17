# CONVENTIONS.md — código do GSI-EBD

## Camadas

- `pages/` e `states/` são **finos**: orquestram, não decidem. Regra de negócio vive em `services/`.
- Acesso a dados via `rx.session()`; nenhuma query monta filtro de tenant por conta
  própria — use `EscopoService`.
- Modelos em `models/` com SQLModel; registrar sempre em `models/__init__.py` (o
  `create_all` depende disso).
- Textos de interface em pt-BR; **código e comentários sem acento** (padrão do repo).

## Testes

- `pytest` em `tests/`. Nome do teste cita o requisito (`test_rf03_...`).
- `tests/test_paginas.py` chama a função de **cada página**: é o gate que pega erro de
  compilação do Reflex (importar o módulo não pega).
- Scripts de importação têm `--autoteste` em SQLite descartável; use antes de produção.
- Ao usar SQLite em teste: `engine.dispose()` antes de apagar o arquivo (Windows).

## Migrations e dados

- Mudança de schema é passo dedicado, nunca efeito colateral de outra tarefa.
- Importadores são **idempotentes** e sem `--apply` não gravam nada.
- O corpus e as referências cruzadas têm origem e licença documentadas — não invente dado.

## UI

- Componentes do Reflex; ícones precisam existir na lista do Lucide (inválido cai para
  `circle_help` silenciosamente).
- Sem regra de negócio no componente; estado explícito de loading/erro/vazio.

## Reflex 0.9.5 — armadilhas já pagas

- Dentro de `rx.foreach` o valor é `Var`: **não concatenar com `+`**; concatene em Python
  no estado ou use f-string de `Var`.
- `import rx` não existe: é `import reflex as rx`.
- `session.exec(select(func.count()))` devolve `Row`; use `session.execute(...).scalar_one()`.
