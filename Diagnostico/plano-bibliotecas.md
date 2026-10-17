# Plano — Obra, Adendos e Estudo (fluxo em cascata)

**v2** — reescrito depois da especificação de 2026-10-16, que corrigiu a leitura
da v1. Nada aqui está implementado.

---

## 1. O modelo, em três artefatos

| Artefato | O que é |
|---|---|
| **OBRA** | A **fonte**: um livro, uma coletânea, ou um estudo condensado de vários livros |
| **CAPÍTULOS da obra** | Divisões da obra, só para o arquivo não ficar extenso |
| **ADENDOS** | Material suplementar — da obra (`ADO-01`) e de cada capítulo (`ADO-01.01`) |
| **ESTUDO** | O artefato **aplicável**, gerado a partir da obra; declara sua origem |
| **CAPÍTULOS do estudo** | Divisões próprias do estudo, que **não necessariamente** correspondem às da obra |

O mapa de origem, como você desenhou:

| ORIGEM | ADENDOS | ESTUDO |
|---|---|---|
| Obra-01 | ADO-01 | Estudo-01 |
| Capítulo-01.01 | ADO-01.01 | Capítulo-01.01 |
| Capítulo-01.02 | ADO-01.02 | Capítulo-01.02 |
| Capítulo-01.03 | ADO-01.03 | Capítulo-01.03 · 01.04 · 01.05 |
| Capítulo-01.04 | ADO-01.04 | Capítulo-01.06 |

Dois fatos que a tabela fixa e que o modelo precisa suportar:

- **Um capítulo da obra pode alimentar VÁRIOS capítulos do estudo** (01.03 → três).
  O inverso (vários da obra num só do estudo) é a mesma relação, no outro sentido.
- **A numeração do estudo é própria e contínua** (01.01 … 01.06), não herda a
  numeração da origem. Quem guarda a origem é o mapa, não o número.

> Observação de forma: na sua tabela o adendo do capítulo 2 aparece como
> `ADO-01.2` e os outros como `ADO-01.03`/`ADO-01.04`. Assumi `ADO-01.0N`
> (dois dígitos) para a ordenação não quebrar.

## 2. O que isso corrige da v1

A v1 dizia "hoje cada capítulo é um `Study`; agrupe os 34 numa `Obra` e está
resolvido". **Estava errado por dois motivos:**

1. A `Obra` não é o estudo — é a **fonte**. Faltava a camada do **ESTUDO**, que é
   o que se aplica ao aluno.
2. Os capítulos do estudo **não são** os capítulos da obra. Uma `Obra` com 34
   capítulos pode gerar um `Estudo` com 40 — e é o mapa que explica isso.

Consequência: não é agrupamento aditivo, é **modelo novo**. A v1 subestimou o
custo; este documento assume o custo real (seção 5).

## 3. O que já existe e serve

| Já existe | Onde | Serve para |
|---|---|---|
| `Ambiente` | `models/turma.py:7` | Biblioteca do coordenador (vira o destino da Ação 2) |
| `AmbienteEstudo` | `models/turma.py:35` | O elo catálogo → ambiente; é o passo 2 em embrião |
| `Equipe.nivel` | `models/turma.py:51` | A ideia de nível por equipe já existe |
| `EquipeInstrutor`, `Turma`, `TurmaMembro` | `models/turma.py:74-114` | Vínculos instrutor/aluno |
| `StudyStatus` | `models/study.py:15` | Estados (proposto, em_revisao, aprovado, rejeitado) reaproveitáveis |
| `Role.REVISOR` | `models/user.py:26` | **Encaixa exatamente na Ação 1** — deixou de ser conflito |
| `Study.prerequisite_study_id` | `models/study.py:41` | Primitivo de sequenciamento |

**Ação 1 é trabalho conjunto de Administrador + Revisor** — e `Role.REVISOR` já
existe com essa função editorial. O conflito que a v1 apontou deixa de existir: o
REVISOR não concorre com o coordenador, ele é a etapa **anterior**.

## 4. Modelo de dados proposto

### 4.1 Fonte

```
Obra                 id, titulo, tipo(livro|coletanea|condensado),
                     descricao, is_active, created_at

ObraCapitulo         id, obra_id, ordem, titulo, conteudo_md
                     unique(obra_id, ordem)

Adendo               id, obra_id, obra_capitulo_id?(null = adendo da obra),
                     codigo("ADO-01" / "ADO-01.03"), titulo, conteudo_md
```

### 4.2 Aplicação

```
Estudo               id, obra_id, titulo, doutrina, descricao,
                     status(proposto|em_leitura|em_ajustes|liberado|devolvido),
                     proposto_por, liberado_por, liberado_em

EstudoCapitulo       id, estudo_id, ordem, titulo, conteudo_md, questions_json
                     unique(estudo_id, ordem)

EstudoCapituloOrigem id, estudo_capitulo_id, obra_capitulo_id, adendo_id?
                     -- o mapa; permite 1:N e N:1 entre obra e estudo
```

### 4.3 Ação 1 — leitura, ressalvas, ajustes

```
LeituraCapitulo      id, estudo_capitulo_id, agendado_para,
                     lido_por, lido_em, status
                     -- "agendar a leitura de cada capítulo"

Ressalva             id, estudo_id, estudo_capitulo_id?(null = global),
                     autor_id, tipo(ressalva|correcao|ajuste),
                     texto, status(aberta|resolvida),
                     resolvida_por, resolvida_em, created_at
```

### 4.4 Ações 2 a 4 (destinos)

```
EstudoNivel          id, estudo_id, nivel(basico|medio|avancado),
                     orientacao        -- "abordagem adequada ao nível"

BibliotecaCoordenador  = AmbienteEstudo + nivel, liberado_por, liberado_em

BibliotecaInstrutor    id, instrutor_id, estudo_id, nivel,
                       liberado(bool S/N), liberado_por,
                       treinamento_em, treinamento_obs

LiberacaoAluno         id, aluno_id, instrutor_id, estudo_id, nivel,
                       liberado(bool), proposto_por, confirmado_por, created_at

CapituloLiberado       id, aluno_id, estudo_id, ordem,
                       liberado_por, liberado_em
                       -- progressão: libera o N+1 ao concluir o N
```

## 5. O custo real: migração dos 34 estudos

O que existe hoje: **34 `Study`**, cada um com um `StudyVersion` (conteúdo + 10
questões), e a lição lê o conteúdo por `StudyVersion` → `load_version_payload`.
Aluno, progresso e fila de revisão apontam para `study_version_id`.

No modelo novo, conteúdo e questões passam a viver no **`EstudoCapitulo`**. Então:

| Passo | O que acontece |
|---|---|
| 1 | Criar `Obra` "Doutrinas Cristãs" + 34 `ObraCapitulo` a partir dos arquivos de `DOUTRINAS_CRISTAS/estudo/capitulo_NN/` (a fonte, que hoje só existe como markdown no repositório) |
| 2 | Criar `Estudo` "Doutrinas Cristãs — Estudo Dirigido" (doutrina a declarar) |
| 3 | Migrar cada `Study`+`StudyVersion` → um `EstudoCapitulo` (conteúdo e questões preservados) |
| 4 | Criar o mapa 1:1 `EstudoCapituloOrigem` (cap. NN da obra → cap. NN do estudo) |
| 5 | Repontar `StudyAssignment`/`UserResponse` de `study_version_id` para o capítulo do estudo |
| 6 | A lição passa a ler `EstudoCapitulo` em vez de `StudyVersion` |

Os passos 5 e 6 são os delicados: mexem no caminho que hoje serve as lições em
produção. Precisam de janela e de teste antes.

> **Vale a pena agora?** Sim, mas com uma condição: fazer o passo 5-6 **depois**
> de importar o modelo novo em paralelo e comparar as duas leituras. Nada é
> apagado até a nova leitura estar provada.

## 6. Fases

| Fase | Entrega | Risco |
|---|---|---|
| **1** | `Obra` + `ObraCapitulo` + `Adendo` + tela de importação/link da obra | Baixo — só adiciona |
| **2** | `Estudo` + `EstudoCapitulo` + o mapa de origem, em paralelo ao modelo atual | Baixo — paralelo |
| **3** | Ação 1: agendamento de leitura, ressalvas, ajustes, liberação (admin + revisor) | Baixo |
| **4** | Migrar a lição para `EstudoCapitulo` e repontar progresso/revisão | **Alto** — window obrigatória |
| **5** | Ação 2: biblioteca do coordenador por nível | Médio |
| **6** | Ação 3: biblioteca do instrutor com `Liberado S/N` + treinamento | Médio |
| **7** | Ação 4: liberação conjunta de alunos | Médio |
| **8** | Progressão por capítulo (`CapituloLiberado`) | Médio |

Cada fase é utilizável sozinha; a Fase 4 é a única com janela de risco.

## 7. Perguntas restantes

**Já respondidas:** Ação 1 = admin + revisor (e o `REVISOR` existente serve);
Obra é a fonte e Estudo é a aplicação; capítulo do estudo ≠ capítulo da obra;
um capítulo da obra pode gerar vários do estudo; numeração do estudo é própria.

**Em aberto:**

1. **Adendo**: ele é **texto para o aluno** (entra no capítulo do estudo) ou
   **nota para o revisor** (material de apoio do processo)? Isso decide se ele
   aparece na lição.
2. **Quem escreve o capítulo do ESTUDO?** O conteúdo nasce por transformação do
   capítulo da obra + adendo (automático/assistido), ou é autoria do
   admin/revisor?
3. **Nível**: material próprio por nível (autoria 3x) ou o mesmo material com
   `orientacao` por nível? (o `EstudoNivel` serve aos dois, mas a autoria muda)
4. **Doutrina**: lista fixa (Batista, Pentecostal, Presbiteriano, Adventista…) ou
   cadastrável? Vale como filtro de catálogo, sem bloquear acesso?
5. **Treinamento (Ação 3)**: registro (data + quem liberou + observação) ou
   módulo com conteúdo e avaliação do instrutor?
6. **Ação 4** (sua mensagem foi cortada em "pelo coordenado…"): liberação e
   classificação dos alunos é decisão conjunta coordenador + instrutor? Quem tem
   a palavra final?
