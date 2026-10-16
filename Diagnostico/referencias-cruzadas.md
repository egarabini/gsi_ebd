# Referências cruzadas do OpenBible — spike de viabilidade

Data: 2026-10-12 · Origem do dado: [openbible.info](https://www.openbible.info/labs/cross-references/) · Licença: **CC-BY 4.0**

## Objetivo

Decidir se vale integrar as referências cruzadas do OpenBible aos planos de estudo
(bloco de "passagens relacionadas" em cada capítulo), e medir isso com o dado real
— não com a descrição de terceiros.

## Método

Scripts de medição em `_openbible/` — área de trabalho **não versionada**, que
também guarda o dataset baixado (ainda sem casa definitiva):

- `spike_referencias.py` — carrega o dataset, valida o mapa de livros contra os
  códigos que existem **de fato** no arquivo e mede a cobertura sobre os 34 planos.
- `verificar_correcao.py` — mede o parser do app sobre os planos reais e compara
  com um mapa independente, para a concordância não ser por construção.

Os números abaixo são o que importa; o passo 3 do plano constrói a versão
versionada e testada.

## O dado

| Item | Valor |
|---|---|
| Arquivo | `cross_references.txt` (TSV), 7,9 MB |
| Colunas | `From Verse` / `To Verse` / `Votes` |
| Pares | 344.799 |
| Versículos de origem distintos | 29.364 |
| Livros | 66 (bate exatamente com o mapa) |
| Chave | OSIS-like: `Gen.1.1`, `Ps.115.15`, `1Cor.13.4` |
| **Destino também é intervalo** | ex.: `Rom.8.5-Rom.8.8`, `Matt.13.11-Matt.13.17` |
| Base | *Treasury of Scripture Knowledge* (domínio público) + votos da comunidade |

O cabeçalho do próprio arquivo já carrega a atribuição:
`#www.openbible.info CC-BY 2026-10-12`.

## Resultado 1 — cobertura: adotar

34 planos, **325 citações**, **175 distintas**, 33 dos 66 livros.

| Corte de votos | Citações cobertas | Média de versículos relacionados |
|---|---|---|
| ≥ 1 | 175 / 175 (**100,0 %**) | 46,1 |
| ≥ 5 | 173 / 175 (98,9 %) | 33,9 |
| ≥ 10 | 169 / 175 (96,6 %) | 21,7 |
| ≥ 20 | 142 / 175 (81,1 %) | 13,6 |

**Nenhuma** citação ficou sem referência cruzada. Exemplos (votos ≥ 10):

```
1Cor 2:14     -> 1Cor.1.18 (68), Rom.8.5-Rom.8.8 (57), Matt.13.11-Matt.13.17 (39)
1Cor 3:10-15  -> Eph.2.20 (44), Isa.28.16 (41), 2Tim.2.19 (30), 1Cor.3.11 (28)
1Cor 6:11     -> 1Cor.1.30 (28), Col.3.5-Col.3.7 (24), 1Cor.1.2 (21)
1Cor 11:23-29 -> John.6.51 (25), Gal.6.4 (22), John.6.53-John.6.58 (20)
```

**Veredito: vale.** O dado é pequeno, a cobertura é praticamente total e ele
reforça o princípio que já seguimos — passagem relacionada é **dado verificado**,
não texto gerado pelo modelo.

**Ressalva de curadoria:** no corte ≥ 10 a média é de 21,7 versículos por citação.
Exibir isso cru é pior que não exibir. A integração precisa de um teto (top 5 por
votos, por exemplo) — é decisão de produto, não de engenharia.

## Resultado 2 — bug vivo no mapeamento de livros

O spike esbarrou num defeito **que já está em produção**, independente desta
integração. O `escritura_service` tem um mapa próprio (`LIVROS`), e ele contradiz a
convenção de abreviaturas que o próprio estudo documenta (`AGENTS.md` do
DOUTRINAS_CRISTAS: **Jo = João**).

| Entrada no plano | O que o app resolve hoje | Correto |
|---|---|---|
| `Jo 3.16` | `Jó 3:16` — **livro errado** | `João 3:16` |
| `Jó 1.21` | `[]` — **descartado** | `Jó 1:21` |
| `Êx 34.6-7` | `[]` — **descartado** (acento) | `Êxodo 34:6-7` |
| `Jn 1.1` | `Jonas 1:1` ✓ | — |
| `Sl 119.18` | `Salmos 119:18` ✓ | — |

Alcance medido nos 34 planos:

- **17 citações** de `Jo` (João) resolvidas como `Jó` — e `Jó 3:16` **existe**, então
  o app exibe o texto errado sem erro nenhum em log;
- **2 citações** descartadas em silêncio por causa do acento (`Êx`);
- **19 de 325 = 5,8 %** das citações erradas ou perdidas.

É o mesmo padrão de falha que vínhamos caçando: errado e silencioso. A causa é
estrutural — existem **três** mapas de livros no projeto
(`escritura_service.LIVROS`/`ALIASES`, `load_biblia.PREFIXO_LIVRO` e agora o do
spike), e nenhum é a fonte da verdade.

## Resultado 3 — a busca por referência não é exata

Achado adjacente, no mesmo caminho: o corpus grava a referência como **texto
exato** no metadado (`referencia: "Joao 3:16"`, montado em `load_biblia.py:230`),
mas `EscrituraService.buscar()` procura por **similaridade semântica**, usando a
referência como consulta — e o documento indexado é só o texto do versículo, sem a
referência. Ou seja: a comparação é entre uma referência curta e o texto de um
versículo, em modelos treinados em inglês.

É por isso que o código precisa de `RAG_SCORE_MIN = 0.55` e `n_results=2`: ele está
compensando uma busca inadequada. O ChromaDB suporta filtro por metadado
(`where={"referencia": "Joao 3:16"}`), que é exato, não depende de embedding e não
tem limiar. **A busca exata existe e não está sendo usada.**

Isso importa duas vezes: corrige o bloco de Escritura *e* é pré-requisito das
referências cruzadas, que precisam casar por identidade de versículo.

## Estado medido da produção (antes deste deploy)

Levantado na VPS em 2026-10-16, antes de reconstruir:

| Item | Estado |
|---|---|
| Site | no ar (`HTTP 200`), Traefik + TLS ok, 5 containers de pé há 9 dias |
| Conteúdo | montado corretamente — o container enxerga os 34 capítulos |
| Banco | populado: 39 estudos, 39 versões, 34 vínculos de ambiente, 5 usuários |
| **ChromaDB** | **zero coleções** |
| Corpus (378 MB) | **ausente na VPS** (está no `.gitignore` do repo de conteúdo) |
| Ollama | **sem modelo baixado** |

Consequência que muda o diagnóstico: o bloco de Escritura **nunca funcionou em
produção** — e não foi pelo embedding trocado (defeito real, mas latente), e sim
porque **não havia índice nenhum**. Carregar o corpus é um passo manual de 378 MB
que ainda não foi feito, e é pré-requisito dos passos 2 e 3.

## Plano proposto (nesta ordem)

1. **Mapa canônico de livros** — ✅ **feito** em `gsi_ebd/utils/livros.py`: os 66
   livros com abreviações (com e sem acento), nome PT e código OSIS. O
   `escritura_service` abandonou o mapa próprio e passou a usar este. Verificado
   com 18 testes (`tests/test_livros.py`) e, sobre os 34 planos reais, **0 citações
   erradas e 0 descartadas** — era 17 e 2.
2. **Busca exata por referência** — trocar a consulta semântica por filtro de
   metadado no caminho das citações (`where={"referencia": ...}`).

   O casamento de nomes já foi **medido**, comparando o mapa canônico com o
   dicionário `PREFIXO_LIVRO` do `load_biblia.py` (a definição do que o corpus
   grava): normalizando os dois lados (sem acento, sem espaço), **63 dos 66 livros
   casam automaticamente** — inclusive os dois que já morderam: `João` → `Joao` e
   `Jó` → `Jo`. Sobram **3 divergências de grafia**, todas nomes legítimos, que
   precisam de apelido explícito:

   | Livro | mapa canônico | corpus |
   |---|---|---|
   | Song | Cântico dos Cânticos | Cantares |
   | Obad | Obadias | Abdias |
   | Phlm | Filemom | Filemon |

   Ou seja, o passo 2 é normalização + uma tabela de 3 apelidos — nada de
   adivinhação. Medido por `_openbible/comparar_nomes_corpus.py`.
3. **Carregar as referências cruzadas** — tabela `cross_reference` no Postgres,
   carregada uma vez (344 mil linhas é trivial). Só então o bloco no plano.

## Onde o dado deve morar

O importador roda **dentro do container**, lendo `/conteudo/ESTUDOS_BIBLICOS`
somente leitura. Então o dado precisa estar nesse clone.

Com **7,9 MB**, este é o caso oposto ao do corpus bíblico (378 MB): cabe no
versionamento, com a atribuição CC-BY que o próprio arquivo já traz. Recomendo
`ESTUDOS_BIBLICOS/DADOS_EXTERNOS/openbible/` com um README de procedência —
evita um `scp` manual a cada deploy.

## O que NÃO adotar

Do estudo de viabilidade original, ficam de fora: os parsers em TypeScript (a
stack é Python/Reflex e o parser PT-BR já existe), o texto ASV como base (é
**inglês** de 1901 — a base é a ACF 2007 já indexada) e o Obsidian como base de
conhecimento do app (é ambiente de autoria; o app lê repo → importador → Postgres).
