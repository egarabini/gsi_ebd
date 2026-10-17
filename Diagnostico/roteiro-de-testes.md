# Roteiro de testes — Didasko

Para validar o que foi construído e publicado. Cada passo traz o **resultado
esperado**; a coluna final diz **o que ele prova**.

- **Endereço:** https://didasko.app.br
- **Antes de começar:** abra a página e faça **Ctrl+Shift+R** (recarregar sem
  cache). A interface foi reconstruída várias vezes hoje; um bundle antigo em
  cache faria você ver o menu velho e concluir que nada mudou.

## Credenciais (todas com `senha123`)

| Perfil | E-mail | Papel |
|---|---|---|
| Admin | `admin@gsi.ebd` | Administrador — cria personas, valida, disponibiliza |
| Coordenador | `coordenador@gsi.ebd` | persona de teste |
| Instrutor | `instrutor@gsi.ebd` | persona de teste (fila de correção) |
| Aluno 1 | `aluno1@gsi.ebd` | persona de teste (vê a lição) |
| Aluno 2 | `aluno2@gsi.ebd` | persona de teste |

> ⚠️ O bloco 7 é trocar essas senhas. Elas estão num repositório e o site é
> público: hoje é acesso administrativo aberto.

## Estado de partida (medido agora)

| | |
|---|---|
| Estudos | 39 (35 **aprovados**, 4 **pendentes**: Cap. 01 a 04) |
| Atribuições a alunos | 0 |
| Respostas para corrigir | 0 |
| Corpus bíblico (ChromaDB) | 31.102 versículos na coleção `biblia_pt_br` |
| Referências cruzadas | 344.799 pares (45.036 com votos ≥ 10) |
| Modelo de IA | `gemma2:9b` (5,4 GB) |

Os 4 pendentes estão assim **de propósito**, para você exercitar a validação.

---

## Bloco 1 — Público, sem login

| # | Passo | Resultado esperado |
|---|---|---|
| 1.1 | Abrir `https://didasko.app.br/` | Landing carrega; nenhum erro na tela |
| 1.2 | Abrir `/homenagens` | Página de homenagens carrega |
| 1.3 | Abrir `/login` | Formulário de acesso |
| 1.4 | Com a sessão encerrada, abrir `/admin` direto | **Redireciona para `/login`** |

> **Prova:** as páginas públicas e a proteção de rota.

---

## Bloco 2 — Admin: o que faltava no fluxo

Entre como **admin** (`admin@gsi.ebd`). Você cai em `/admin`.

### 2.A — O menu lateral (o defeito que você apontou)

| # | Passo | Resultado esperado |
|---|---|---|
| 2.1 | Olhar o menu lateral | **5 itens, rótulos distintos:** Gestores · Coordenadores · **Aprovação de Estudos** · **Leads** · **Disponibilizar Estudos** |
| 2.2 | Não deve existir | "Coordenadores" repetido, nem "Relatórios" |
| 2.3 | Clicar em **Aprovação de Estudos** | Abre `/admin` **já na aba de aprovação** (não na primeira) |
| 2.4 | Clicar em **Leads** | Abre a aba Leads |
| 2.5 | Clicar em **Coordenadores** | Abre a aba Coordenadores |

> **Prova:** antes os itens apontavam para `/admin` **sem selecionar aba** — dois
> com o mesmo rótulo e um ("Relatórios") para lugar nenhum. O menu parecia
> funcionar e não fazia nada.

### 2.B — Validar (o admin passa a validar o que entra)

| # | Passo | Resultado esperado |
|---|---|---|
| 2.6 | Na aba de aprovação | **4 estudos pendentes:** Cap. 01, 02, 03 e 04 |
| 2.7 | Clicar em **Aprovar** no Cap. 01 | Mensagem de sucesso; ele **sai da fila**; sobram 3 |
| 2.8 | Clicar em **Rejeitar** no Cap. 02 **sem** escrever motivo | Mensagem de erro pedindo o motivo (não rejeita) |
| 2.9 | Escrever um motivo e clicar **Rejeitar** | Estudo sai da fila como rejeitado |
| 2.10 | Com os pendentes restantes, clicar **"Aprovar todos os pendentes"** | Todos saem da fila de uma vez; mensagem com a quantidade |

> **Prova:** o importador **não aprova mais sozinho** — ele grava `PROPOSTO` e o
> admin decide. Antes, os 39 estudos entraram `APROVADO` e a fila nasceu vazia.
> Para reconferir do zero: rode o importador e os capítulos voltam a aparecer aqui.

### 2.C — Disponibilizar (o admin também entrega ao aluno)

| # | Passo | Resultado esperado |
|---|---|---|
| 2.11 | Menu → **Disponibilizar Estudos** | Abre `/coordenador`; o **título da página diz "Disponibilizar Estudos"** |
| 2.12 | Olhar a lista "Meus Alunos" | **`aluno1@gsi.ebd` e `aluno2@gsi.ebd`** aparecem |
| 2.13 | Marcar `aluno1` e escolher no select **`26:Cap. 21 — Conversão (Fé e Arrependimento)`** | O select lista só estudos **aprovados** (não deve aparecer Cap. 01–04 se ainda pendentes) |
| 2.14 | Clicar **Atribuir Estudo** | Mensagem de sucesso, com a quantidade atribuída |
| 2.15 | Clicar **Atribuir Estudo** de novo, mesmo aluno e estudo | Mensagem "Todos os alunos já possuem este estudo" (não duplica) |

> **Prova:** a tela vinha **vazia** para o admin (ela filtrava alunos por
> "instrutores e turmas que apontam para mim"). Agora o admin vê todos — é o que
> permite disponibilizar sem depender de persona fake.

---

## Bloco 3 — Aluno: a lição (é aqui que se vê o resultado)

Saia e entre como **`aluno1@gsi.ebd`**.

| # | Passo | Resultado esperado |
|---|---|---|
| 3.1 | Abrir `/aluno` | O card **"Cap. 21 — Conversão (Fé e Arrependimento)"** aparece |
| 3.2 | Clicar **"Iniciar Estudo"** | **Abre a página da lição** e o conteúdo do capítulo aparece |
| 3.3 | Rolar até depois do conteúdo | Cartão **"Escritura"** (fundo lilás) |

### 3.A — Bloco de Escritura (o bug do `Jo` virando `Jó`)

Esperado: **4 passagens, nesta ordem**, com o texto do corpus (ACF 2007):

1. `**Marcos 1:15**` — *E dizendo: O tempo está cumprido, e o reino de Deus está próximo. Arrependei-vos, e crede no evangelho.*
2. `**Atos 20:21**` — *Testificando, tanto aos judeus como aos gregos, a conversão a Deus, e a fé em nosso Senhor Jesus Cristo.*
3. `**João 3:16**` — *Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito…*
4. `**Hebreus 11:1**` — *ORA, a fé é o firme fundamento das coisas que se esperam…*

**O teste que importa:** o item 3 tem de dizer **João 3:16** com o texto *"Porque
Deus amou o mundo…"*. Se aparecer **Jó 3:16**, a correção do mapa de livros não
está no ar. E o rótulo tem de vir **com acento** ("João", não "Joao").

> **Prova:** o mapa de abreviações resolvia `Jo` como **Jó**. Medido nos 34
> planos, 17 citações apontavam para o livro errado e 2 eram descartadas.

### 3.B — Bloco de Passagens relacionadas (novo)

Esperado: cartão azul com **exatamente 5** passagens e a linha de atribuição
`referências cruzadas: OpenBible.info, CC-BY 4.0`:

1. `**Romanos 5:8**` — *Mas Deus prova o seu amor para conosco…*
2. `**2 Coríntios 5:7**` — *(Porque andamos por fé, e não por vista).*
3. `**Mateus 3:2**` — *E dizendo: Arrependei-vos, porque é chegado o reino dos céus.*
4. `**1 João 4:9-10**` — intervalo: traz o texto **dos dois versículos**
5. `**2 Coríntios 4:18**` — *Não atentando nós nas coisas que se vêem…*

**Os testes:** são **5** (o teto que você definiu); a **atribuição CC-BY** aparece
(obrigação da licença); nenhuma delas é passagem que o próprio plano já cita; o
intervalo do item 4 traz os dois versículos.

> **Prova:** é o dado do OpenBible com o texto vindo do corpus — passagem
> relacionada é dado verificado, nunca texto gerado pelo modelo.

### 3.C — Responder até o fim

| # | Passo | Resultado esperado |
|---|---|---|
| 3.4 | Responder as 10 questões | 1 objetiva e 1 de preenchimento **corrigem na hora**; as **8 abertas** vão para a fila do instrutor |
| 3.5 | Ao responder uma questão aberta | Mensagem dizendo que será avaliada pelo instrutor (não conta como acerto) |
| 3.6 | Chegar ao fim (responder a última) | "Estudo Concluído!" e o estudo **sai da lista** de disponíveis |

---

## Bloco 4 — Correção e IA

Entre como **`admin@gsi.ebd`** (o admin vê todos os alunos) ou `instrutor@gsi.ebd`.

| # | Passo | Resultado esperado |
|---|---|---|
| 4.1 | Abrir `/revisao` | A fila mostra as respostas abertas do `aluno1` no Cap. 21 |
| 4.2 | Abrir uma resposta | Texto da resposta + campo de parecer |
| 4.3 | Clicar **"Sugerir com IA"** | Depois de **dezenas de segundos**, um parecer preliminar e a aderência |
| 4.4 | Editar ou descartar a sugestão | A sugestão é sua para revisar — não vai direto ao aluno |
| 4.5 | Enviar o parecer | "Parecer enviado ao aluno!" |
| 4.6 | Entrar como `aluno1` → `/aluno/pareceres` | O parecer aparece para o aluno |

> **Prova:** a IA é **apoio**, com revisão humana obrigatória. Sem GPU (6 vCPUs),
> a geração é lenta de propósito: se incomodar, troque `OLLAMA_MODEL` por um
> modelo 3B.

---

## Bloco 5 — Regressão (o que não podia quebrar)

| # | Passo | Resultado esperado |
|---|---|---|
| 5.1 | Entrar como `coordenador@gsi.ebd` → `/coordenador` | Título "Painel do Coordenador" (**não** "Disponibilizar Estudos") |
| 5.2 | Menu dele | Ambiente · Instrutores · Catálogo · Progresso |
| 5.3 | Lista de alunos dele | Continua funcionando como antes |
| 5.4 | Atribuir um estudo como coordenador | Funciona igual (a rota dele não mudou) |

> **Prova:** a mudança do admin não alterou o fluxo do coordenador.

---

## Bloco 6 — Segurança (fazer **depois** dos testes)

| # | Passo | Resultado esperado |
|---|---|---|
| 6.1 | `/perfil/alterar-senha` com cada usuário | Senha trocada |
| 6.2 | Sair e entrar com a senha nova | Acesso normal |
| 6.3 | `admin@gsi.ebd` / `senha123` | **Não** deve mais funcionar |

---

## Se algo falhar

**Logs do app** (na VPS, como `eduardo`):

```bash
cd ~/didasko
sudo docker compose --env-file .env -f deploy/docker-compose.producao.yml logs --tail 60 app
```

| Sintoma | O que verificar |
|---|---|
| Menu ainda velho | Ctrl+Shift+R; depois confirme o deploy |
| Cartões não aparecem na lição | Você está em `/aluno/licao`? O botão "Iniciar Estudo" leva até lá |
| Cartões vazios | `sudo docker compose ... exec app python -c "import chromadb; c=chromadb.HttpClient(host='chromadb',port=8000); print([(x.name,x.count()) for x in c.list_collections()])"` — deve mostrar `biblia_pt_br 31102` |
| "Sugerir com IA" não responde | `sudo docker compose ... exec ollama ollama list` — deve listar `gemma2:9b` |
| Estudo não aparece para o aluno | Ele foi **atribuído**? O estudo está **aprovado**? (as duas condições) |

## Ficha de registro

| Bloco | Passou | Observação |
|---|---|---|
| 1 — Público | ☐ | |
| 2 — Admin: menu | ☐ | |
| 2 — Admin: validar | ☐ | |
| 2 — Admin: disponibilizar | ☐ | |
| 3 — Lição: Escritura | ☐ | |
| 3 — Lição: relacionadas | ☐ | |
| 3 — Lição: responder | ☐ | |
| 4 — Revisão + IA | ☐ | |
| 5 — Regressão | ☐ | |
| 6 — Senhas | ☐ | |
