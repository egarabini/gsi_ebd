# PROJECT_CONTEXT.md — GSI-EBD

## O que é este repositório

O **código** da plataforma Didasko: Reflex (front+back em Python) + PostgreSQL +
ChromaDB + Ollama, empacotado em Docker e publicado por Traefik.

## Stack

Python 3.12 · Reflex 0.9.5 · SQLModel/SQLAlchemy 2 · PostgreSQL 16 · ChromaDB ·
Ollama (`gemma2:9b`) · Docker Compose + Traefik · pytest.

## O que NÃO mudar

- **Stack** (ADR-001): nada de Node/TS na aplicação.
- **Corpus** (ADR-002): `:ro`, fora do repositório e da imagem.
- **Caminho da Escritura** (ADR-003): busca por igualdade no metadado; semântica só por assunto.
- **Deploy** (ADR-010): não é este repositório que publica; é o GitHub Actions.
- O `.env` de produção fica **só na VPS** (ADR-008).

## ADRs vigentes

`documentacao/adr/` — 001 a 011. Em especial: 003 (Escritura), 005 (Obra/Estudo)
e 011 (aprovação assinada) regem o modelo de conteúdo.

## Estado atual (para não redescobrir)

- 31.102 versículos indexados; 344.799 referências cruzadas carregadas.
- 39 estudos (34 capítulos do Grudem + 5 de exemplo); 5 usuários de demonstração.
- 76 testes; `tests/test_paginas.py` é o gate de compilação das páginas.
- Deploy: `deploy/subir.sh` (hoje executado à mão; vira runbook do workflow).
