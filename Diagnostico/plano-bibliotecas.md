# Plano — fluxo de bibliotecas em cascata

Especificação do Eduardo (2026-10-16), traduzida em modelo e fases. **Nada aqui
está implementado**: este documento existe para fechar as decisões que mudam o
desenho antes de escrever código.

---

## 1. O que eu entendi

Quatro ações encadeadas, cada uma liberando para o nível seguinte:

| Ação | Quem faz | O que entra | O que sai | Estado |
|---|---|---|---|---|
| **1** | Coordenador | Estudos do catálogo (agrupados por capítulo, classificados por nível e doutrina) | Estudo **avaliado**, com comentários globais e por capítulo | `em_avaliacao` → `avaliado` |
| **2** | Coordenador | Estudo avaliado | Estudo na **biblioteca do coordenador**, classificado por nível (até 3: Básico/Médio/Avançado) | `na_biblioteca_coordenador` |
| **3** | Coordenador | Estudo da sua biblioteca | Estudo na **biblioteca do instrutor**, com `Liberado S/N` — depende do treinamento dado ao instrutor | `liberado_instrutor` |
| **4** | Coordenador **+** instrutor (em conjunto) | Estudo liberado + alunos | **Alunos liberados e classificados** por instrutor | `liberado_aluno` |

E duas regras transversais:

- **Progressão por capítulo**: o aluno começa no capítulo 1; ao concluir, o
  avaliador libera o capítulo 2, e assim por diante. Capítulo não é unidade de
  seleção — é etapa do aluno dentro do estudo.
- **Comentários em dois níveis**: globais para o estudo (orientação aos
  instrutores) e específicos por capítulo.

---

## 2. O que já existe (reaproveitar, não recriar)

| Já existe | Onde | Serve para |
|---|---|---|
| `Ambiente` (tenant do coordenador) | `models/turma.py:7` | É a **biblioteca do coordenador** em embrião |
| `AmbienteEstudo` (estudo escolhido pelo ambiente) | `models/turma.py:35` | O elo catálogo → biblioteca do coordenador **já é o passo 2** |
| `Equipe` com campo **`nivel`** | `models/turma.py:51` | Agrupamento de instrutores por nível — a ideia de nível já existe |
| `EquipeInstrutor` | `models/turma.py:74` | Vínculo instrutor ↔ equipe |
| `Turma` / `TurmaMembro` | `models/turma.py:85` | Agrupamento e histórico de alunos |
| `User.coordenador_id` / `instrutor_id` | `models/user.py:112` | Hierarquia de cadastro |
| `StudyStatus.EM_REVISAO` | `models/study.py:18` | Estado de avaliação já previsto |
| **`Role.REVISOR`** | `models/user.py:26` | Função editorial de validar o catálogo — **atenção**: conflita com "quem avalia é o coordenador" |
| `Study.prerequisite_study_id` | `models/study.py:41` | Primitivo de sequenciamento |
| `Study.category` / `Study.level` | `models/study.py:28,31` | Classificação já carregada pelo importador |

**Consequência:** boa parte da hierarquia existe. O que falta é o **fluxo** entre
os níveis, não os níveis.

---

## 3. O que falta, por ação

**Ação 1**
- Não há classificação de **doutrina** no estudo (`category` é texto livre, e
  `User.profissao_fe` é do usuário, não do estudo).
- Não há **agrupamento por capítulo**: hoje **cada capítulo é um `Study`** — 34
  estudos separados, não 1 estudo com 34 capítulos. É a maior divergência.
- Não há **comentários** (globais nem por capítulo).
- Não há registro de "quem é o coordenador avaliador" do estudo.

**Ação 2**
- `Study.level` é **um** valor. O modelo pede "até 3 níveis com abordagem
  adequada" — ou seja, oferta por nível, não rótulo único.
- `AmbienteEstudo` não tem nível por ambiente (o mesmo estudo em Básico num
  ambiente e Avançado em outro).

**Ação 3**
- Não existe biblioteca do instrutor, nem `Liberado S/N`, nem registro de
  treinamento.

**Ação 4**
- `User.instrutor_id` existe, mas não há fluxo de liberação conjunta
  (coordenador + instrutor) nem classificação do aluno por instrutor.

---

## 4. As três decisões que mudam tudo

### 4.1 Capítulo: agrupar ou refatorar?

**Hoje:** 34 capítulos = 34 `Study`. **O modelo pede:** 1 estudo com capítulos.

| Caminho | O que é | Custo | Risco |
|---|---|---|---|
| **A) Aditivo — `Obra`** | Nova tabela `Obra` agrupa `Study` existentes com `ordem`; o capítulo continua sendo um `Study` | Baixo. Nada migra; assignment, progresso e revisão continuam válidos | A palavra "capítulo" fica sendo um `Study` — quem ler o banco precisa saber |
| **B) Refatorar — `Capitulo` dentro de `Study`** | `Study` = a obra; `Capitulo` = conteúdo + questões; versão passa a ser do capítulo | Alto. Mexe em assignment, progresso, fila de revisão e no importador | Migração de conteúdo em produção |

> **Recomendação: A.** Entrega o fluxo (seleção por obra, progressão por ordem)
> sem migrar conteúdo nem reescrever a lição. Dá para ir para B depois, com o
> sistema já em uso e a dor de migração medida.

### 4.2 Nível: conteúdo próprio ou metadado?

- **Se for rótulo**: 1 conteúdo, marcado como ministrável em Básico/Médio/Avançado,
  com orientação de abordagem por nível. Barato.
- **Se for conteúdo**: 3 materiais distintos (texto e questões adaptados) — é
  autoria 3x, e o modelo precisa apontar para versões diferentes.

> **Recomendação:** modelar `ObraNivel(obra, nivel, versao_id, orientacao)` — hoje
> `versao_id` aponta para a mesma versão (rótulo + orientação); quando houver
> material adaptado, aponta para outra. Um só desenho, os dois futuros.

### 4.3 Doutrina: filtro ou portão?

- **Filtro**: o coordenador vê o catálogo e filtra por tradição (Batista,
  Pentecostal, Presbiteriano, Adventista…). Todo mundo pode escolher qualquer um.
- **Portão**: o ambiente declara sua tradição e só enxerga estudos compatíveis.

> **Recomendação:** **filtro** (com a tradição do ambiente como default do
> filtro). Portão transforma uma decisão pedagógica em restrição de acesso — e o
> coordenador pode querer usar um estudo de outra tradição com ressalvas, que é
> exatamente o que os comentários da Ação 1 servem para registrar.

---

## 5. Modelo proposto (aditivo)

```
Obra                      -- NOVO: o estudo como curso (agrupa capítulos)
  id, titulo, doutrina, descricao, is_active

ObraCapitulo              -- NOVO: liga Obra -> Study existente, com ordem
  obra_id, study_id, ordem, titulo_no_estudo
  unique(obra_id, ordem)

ObraNivel                 -- NOVO: oferta por nível
  obra_id, nivel, study_version_id?, orientacao

ObraComentario            -- NOVO: comentários do coordenador (Ação 1)
  obra_id, capitulo_ordem (nullable = global), autor_id, texto, created_at

AvaliacaoObra             -- NOVO: a Ação 1 (estado + avaliador)
  obra_id, coordenador_id, estado(em_avaliacao|avaliado|devolvido),
  parecer, iniciado_em, concluido_em

BibliotecaCoordenador     -- EVOLUIR AmbienteEstudo: + nivel, + liberado_em

BibliotecaInstrutor       -- NOVO: Ação 3
  instrutor_id, obra_id, nivel, liberado(bool), liberado_por,
  treinamento_em, treinamento_obs

LiberacaoAluno            -- NOVO: Ação 4
  aluno_id, instrutor_id, obra_id, nivel, liberado(bool),
  liberado_por, aprovado_por_coordenador(bool), created_at

CapituloLiberado          -- NOVO: progressão por capítulo
  aluno_id, obra_id, ordem, liberado_por, liberado_em
```

O `Study`/`StudyVersion`/`StudyAssignment`/`UserResponse` **não mudam** — é o que
mantém a migração em zero.

---

## 6. Migração dos 34 estudos que já existem

1. Criar `Obra` "Doutrinas Cristãs" com `doutrina` a declarar (ver pergunta 3).
2. Ligar os 34 `Study` existentes como `ObraCapitulo`, na ordem do título
   (`Cap. 01` … `Cap. 34`).
3. Criar `ObraNivel` para os níveis que o coordenador declarar.
4. `AmbienteEstudo` existente vira `BibliotecaCoordenador` com nível herdado do
   `Study.level`.

Nada é reescrito: o que está em produção continua servindo as lições.

---

## 7. Entrega em fases

| Fase | Entrega | Depende de |
|---|---|---|
| **1** | `Obra` + `ObraCapitulo` + migração dos 34; tela do admin para agrupar | 4.1 |
| **2** | Ação 1: doutrina, seleção da obra para avaliação, comentários globais e por capítulo, estado | 4.3 |
| **3** | Ação 2: biblioteca do coordenador por nível | 4.2 |
| **4** | Ação 3: biblioteca do instrutor com `Liberado S/N` + registro de treinamento | — |
| **5** | Ação 4: liberação conjunta de alunos + classificação por instrutor | — |
| **6** | Progressão por capítulo (liberar o N+1 ao concluir o N) | Fase 1 |

Cada fase é utilizável sozinha — nenhuma deixa o produto num meio-termo quebrado.

---

## 8. Perguntas que travam o desenho

1. **Quem faz a Ação 1?** O texto diz "disponibilizados para avaliação do
   coordenador" e "o Coordenador já vem pré-selecionado pelo login" — leio que
   **o coordenador marca e avalia**. Mas o código tem `Role.REVISOR` ("valida,
   junto com o Administrador, os estudos que entram no catálogo"). São dois
   momentos (catálogo × biblioteca) ou o REVISOR deixa de existir?
2. **Capítulo:** confirma o caminho **aditivo** (`Obra` agrupando os 34 `Study`),
   ou você quer mesmo `Capitulo` dentro do estudo?
3. **Nível:** "abordagem adequada ao modelo definido" significa **material
   próprio por nível** (autoria 3x) ou **o mesmo material com orientação de
   abordagem** por nível?
4. **Doutrina:** filtro de catálogo ou portão de acesso? E a lista é fixa
   (Batista, Pentecostal, Presbiteriano, Adventista…) ou cadastrável?
5. **Treinamento (Ação 3):** é um registro (data + quem liberou + observação) ou
   um módulo de treinamento com conteúdo e avaliação do instrutor?
6. **Ação 4 (sua mensagem foi cortada em "pelo coordenado…"):** a liberação e a
   classificação dos alunos é uma decisão **conjunta** (coordenador propõe,
   instrutor confirma — ou o inverso)? Quem tem a palavra final?
