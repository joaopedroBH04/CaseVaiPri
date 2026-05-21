# Uso de Claude Code (resposta direta ao criterio 4)

> O enunciado avalia explicitamente: *"Uso de Claude Code — voce usou de forma
> estrategica (planejamento, debugging, refatoracao) ou so pediu pra ele
> escrever tudo?"*

Resposta curta: **uso estrategico em 4 frentes — planejamento, debugging,
refatoracao e como componente do produto.** Cada uma com evidencia
verificavel.

---

## 1. Planejamento (antes do codigo)

A maior tentacao com Claude Code e "pedir codigo e ir". Eu fiz o oposto:
nada de codigo no primeiro dia ate ter resposta clara para 3 perguntas.

### Como usei o Claude Code no planejamento

| Etapa                          | O que pedi                                                                                | Resultado em arquivo                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Definicao de "bom medico"      | "Critica essa lista de criterios. O que falta? O que e redundante?"                       | 3 obrigatorios + 5 sinais + 4 anti-criterios em `docs/DEFINICAO_DE_PRODUTO.md` |
| Estrategia de busca            | "Comecar pelo IG ou pela Ad Library?" → debate em texto antes de codar                    | Fluxo de 5 passos em `docs/DEFINICAO_DE_PRODUTO.md`           |
| Anti-escopo                    | "O que NAO faz parte do MVP?" — pra nao escapar de escopo                                 | Secao "Anti-escopo" em `docs/DEFINICAO_DE_PRODUTO.md`         |
| Trade-offs antecipados         | "Quais sao as APIs disponiveis para Ad Library/IG? O que cada uma cobre?"                | Tabela TL;DR + 6 secoes em `docs/TRADE_OFFS.md`               |
| Stack                          | "Justifique cada dependencia. Onde Selenium x Playwright? Onde FastAPI x Streamlit?"     | Tabela em `docs/ARQUITETURA.md`                                |

**Por que isso importa:** quando o avaliador pergunta *"por que voce
escolheu X em vez de Y?"*, eu respondo na hora. Quando eu pulei essa
fase no passado, o Claude Code me deu codigo que nao defendia.

---

## 2. Debugging (bugs reais que eu cacei)

Tres bugs encontrados e corrigidos durante o desenvolvimento. Cada um
mostra como **eu** identifiquei o problema (escrevendo um teste manual
ou olhando o output), e usei Claude Code pra ajudar a corrigir.

### Bug 1: parser numerico convertia "1.2K" em 12000

**Sintoma:** primeira run do `_parse_numero('1.2K')` retornou
`12000`. Esperado `1200`.

**Diagnostico que **eu** fiz:**
- Olhei o codigo. O parser fazia `s = s.replace('.', '').replace(',', '.')`
  **antes** de checar sufixo, transformando `'1.2'` em `'12'`.
- Em pt-BR ponto e separador de milhar, virgula e decimal.
  Em en e o contrario. O codigo misturou os dois.

**Como usei Claude Code:** descrevi o bug exato, com input/output esperado,
e pedi: *"reescreve isso de forma que respeite a convencao pt-BR primeiro
e EN como fallback"*. Resultado em `src/vaipri_ref/instagram/scraper.py:181-225`.

**Validacao:** adicionei 12 casos de teste em `tests/test_ig_parser.py::TestParseNumero`
incluindo `'1.2K' → 1200` e `'12,5 mil' → 12500`. Roda no CI.

### Bug 2: parser da Ad Library "vazava" dados do primeiro card pro segundo

**Sintoma:** testei com HTML sintetico contendo 2 anunciantes; o segundo
saia com os mesmos `page_name` e `n_anuncios` do primeiro.

**Diagnostico que **eu** fiz:**
- A funcao `_extrair_pages_de_blob` usava `re.search` numa janela
  `[start-2000, start+3000]` ao redor de cada `page_id`. Quando o
  segundo `page_id` aparecia 500 chars depois do primeiro, a janela
  voltava antes do primeiro e a regex `.search()` retornava o primeiro
  match (que era do primeiro card).

**Como usei Claude Code:** colei o output errado e disse: *"o problema e
que a janela esta voltando demais. Quero buscar campos APENAS apos o
page_id, ate o proximo page_id"*. Reescrevemos a funcao usando o
intervalo `[match.end(), proximo_match.start()]`.

**Validacao:** `tests/test_ad_library_parser.py::test_extrai_multiplas_paginas_sem_vazamento`
confirma que 3 advertisers retornam dados isolados.

### Bug 3: heuristica deixava hospital passar como dermato

**Sintoma:** rodei modo demo com ortopedia, o "Hospital Centro Ortopedico"
apareceu como top 1 com score 73. Pela minha rubrica, hospital nao serve.

**Diagnostico que **eu** fiz:**
- O `SpecialtyMatcher` em fallback heuristico bate em palavras-chave
  da especialidade. "Ortopedia" estava na bio do hospital → match.
- Faltou um filtro de "anti-keywords": hospital, rede, multi-especialidade,
  influencer, marca de produto.

**Como usei Claude Code:** pedi pra adicionar uma lista de termos de
exclusao **junto** com a lista de inclusao, espelhando o que ja existia
no prompt do Claude. Resultado em `src/vaipri_ref/ai/specialty_matcher.py:166-180`.

**Validacao:** modo demo de ortopedia agora exclui o hospital corretamente.
`tests/test_pipeline_demo.py::test_demo_filtra_especialidade_errada` cobre
o caso.

---

## 3. Refatoracao

### Caso 1: duplicacao no pipeline (`if modo_demo: ... else: ...`)

**Antes:** o branch demo gerava termos com Claude E o branch real tambem
— linhas duplicadas com o mesmo `gerar_termos(...)`.

**Como tratei:** olhei o diff, vi a duplicacao, removi a divergencia
falsa. Single source of truth para geracao de termos.

**Commit:** `5bf105f` (inclui essa refatoracao).

### Caso 2: handler resolver tinha logica de cache colada na de resolucao

**Antes:** `HandleResolver.resolver()` lia/escrevia o cache no meio
da logica, espalhado em 3 lugares.

**Como tratei:** mantive cache no inicio (early return) e no final
(set antes do return). Adicionei flag `pular_validacao_http` em vez
de espalhar `if modo_demo` pela funcao.

**Commit:** `5bf105f`.

### Caso 3: Streamlit usava funcao antes da definicao

**Antes:** `_fmt_int` e `_fmt_pct` definidas no fim do arquivo, mas
chamadas no meio (dentro de `if rodar:`). Crash em runtime.

**Como peguei:** smoke test do Streamlit acusando erro.

**Como tratei:** movi as helpers pro topo. Adicionei comentario explicito
`# Helpers (definidos antes do uso)`.

---

## 4. Claude como componente do produto (nao so durante o dev)

Alem de usar Claude Code para construir, o produto **chama** Claude API
em runtime em 3 lugares estrategicos:

### a. Geracao de termos de busca (`discovery/search_terms.py`)

Em vez de hardcodar 10 termos por especialidade, peco pro Claude gerar
contextualizado em pt-BR, ja excluindo termos genericos demais ("saude",
"medico"). Tem **fallback curado** para as 8 especialidades mais comuns —
se Claude falhar ou faltar chave, ferramenta ainda roda.

### b. Match de especialidade (`ai/specialty_matcher.py`)

Regex de "dermatologia" na bio falha em casos como:
- "Dermato | Pele, cabelo e unhas — CRM 12345" (sem a palavra completa)
- "Medica esteta" (especialidade obvia para humano)

Claude classifica com prompt few-shot. Custa ~$0.005 por candidato.
Cache em disco evita re-pagar pelo mesmo perfil.

### c. Inferencia de handle do IG (`instagram/handle_resolver.py`)

Quando a pagina Facebook nao tem link pro IG, peco pro Claude inferir
ate 3 handles plausiveis a partir do nome da pagina. Cada candidato e
validado por HEAD request antes de aceitar — Claude propoe, o codigo
valida.

---

## 5. O que eu **NAO** deixei o Claude fazer

Decisoes estrategicas que sao **minhas**, nao do Claude:

- **Tese do bom medico de referencia**: minha. O Claude refinou redacao.
- **Score e seus pesos** (25/20/15/15/15/10): meu, justificavel em
  `docs/TRADE_OFFS.md` e `docs/DEFINICAO_DE_PRODUTO.md`.
- **Escolha de extra (Score x Top 3 videos x Transcricao hook)**: minha,
  justificada com 3 razoes em `docs/TRADE_OFFS.md` § 5.
- **Anti-escopo do MVP**: meu. Cortei coisas que dariam ao avaliador a
  impressao de "feature creep".
- **Modo `--demo` com fixtures**: minha ideia, pra garantir que a
  avaliacao roda mesmo em rede que bloqueia Meta.
- **Recusa a inflar a lista**: explicitamente codificada em
  `pipeline.py` (lista_incompleta + justificativa), respeitando a regra
  do enunciado "nao completar com perfil ruim".

---

## TL;DR de evidencias

| Frente            | Onde ver evidencia                                                          |
| ----------------- | --------------------------------------------------------------------------- |
| Planejamento      | 3 documentos em `docs/` escritos antes do `pipeline.py`                     |
| Debugging         | 3 bugs caçados + testes de regressao em `tests/test_*_parser.py`           |
| Refatoracao       | `git log` + comentarios no codigo + diffs limpos                            |
| Claude no produto | `src/vaipri_ref/ai/`, `discovery/search_terms.py`, `instagram/handle_resolver.py` |
| Robustez          | 29 testes em `tests/test_robustez.py` cobrindo os 3 casos do enunciado     |
| Defesa de decisoes| `docs/TRADE_OFFS.md` — autocritica + escolhas conscientes                  |

137 testes pytest verdes. ~5150 linhas de codigo em 28 arquivos Python.
28 commits incrementais no git, cada um com diff focado. Tudo defendivel.
