# Buscador de Referencias de Trafego Pago (VaiPri)

Ferramenta que recebe **@ do Instagram do cliente + especialidade medica**
e devolve **ate 10 medicos** da mesma especialidade que **rodam anuncios
ativos no Meta agora**, com metricas de perfil, link direto pros anuncios
e score de 0–100.

Construida para a case do **Analista de Automacao** da VaiPri.

```
$ vaipri-ref buscar @clinica.exemplo dermatologia

  Referencias — Dermatologia (Top 10)
 ╓────┬─────────────────────┬────────────────────┬─────┬────────────┬───────╖
 ║ #  │ Instagram           │ Nome               │ Ads │ Seguidores │ Score ║
 ╟────┼─────────────────────┼────────────────────┼─────┼────────────┼───────╢
 ║ 1  │ @draanalima.derm    │ Dra. Ana Lima      │  22 │     187.5k │   69  ║
 ║ 2  │ @dr.pedrosalles     │ Dr. Pedro Salles   │  14 │      85.4k │   67  ║
 ║ …  │ …                   │ …                  │  …  │       …    │   …   ║
 ╙────┴─────────────────────┴────────────────────┴─────┴────────────┴───────╜
```

---

## O que esta neste repo

```
├── docs/
│   ├── DEFINICAO_DE_PRODUTO.md   ← O DOC DO CASE (criterios + estrategia + outcome)
│   ├── ARQUITETURA.md            ← Como o codigo se organiza
│   └── TRADE_OFFS.md             ← Por que cada escolha + limites conhecidos
├── src/vaipri_ref/               ← Pacote Python
│   ├── pipeline.py               ← Orquestrador
│   ├── discovery/                ← Termos + Meta Ad Library scraper
│   ├── instagram/                ← Scraper publico do IG
│   ├── ai/                       ← Wrapper do Claude + classificador
│   ├── scorer.py                 ← Score 0-100 (extra escolhido)
│   ├── reporter.py               ← JSON, Markdown, HTML
│   ├── cli.py                    ← `vaipri-ref` CLI
│   └── demo/fixtures.py          ← Dados sinteticos pra modo offline
├── app/streamlit_app.py          ← UI web
├── outputs/exemplos/             ← Saidas geradas para 3 especialidades de teste
└── tests/                        ← 71 testes pytest
```

**Comece por:** [`docs/DEFINICAO_DE_PRODUTO.md`](./docs/DEFINICAO_DE_PRODUTO.md).
Ele responde "o que faz uma boa referencia" e como busco, antes de qualquer codigo.

**Para o Loom (5min):** [`docs/ROTEIRO_LOOM.md`](./docs/ROTEIRO_LOOM.md) — roteiro de
gravacao bloco a bloco com tempos-alvo, falas e comandos prontos pra copy/paste.

---

## Instalacao em 3 passos

### 1) Clone e crie um virtualenv

```bash
git clone <este-repo> && cd CaseVaiPri
python3 -m venv .venv && source .venv/bin/activate
```

### 2) Instale dependencias

```bash
pip install -r requirements.txt
# Para o scraping real da Meta, instala Chromium para o Playwright:
python -m playwright install chromium
```

### 3) Configure o .env

```bash
cp .env.example .env
# edite e cole sua ANTHROPIC_API_KEY
```

**Onde pegar a chave da Anthropic:** [console.anthropic.com](https://console.anthropic.com).
Sem a chave, a ferramenta ainda roda (modo heuristico), mas a qualidade do match de especialidade cai.

---

## Como rodar

### Opcao A — CLI (recomendado para teste)

```bash
# busca real (precisa de rede aberta para Meta + chave Anthropic)
vaipri-ref buscar @clinica.exemplo dermatologia

# ou, durante avaliacao em rede restrita:
vaipri-ref buscar @clinica.exemplo dermatologia --demo

# abre o HTML gerado no navegador no fim:
vaipri-ref buscar @clinica.exemplo dermatologia --demo --abrir-html

# logs detalhados:
vaipri-ref buscar @clinica.exemplo dermatologia --demo -v
```

Sem instalar o pacote? Use `python -m`:

```bash
PYTHONPATH=src python -m vaipri_ref buscar @clinica.exemplo dermatologia --demo
```

**Saidas geradas em `outputs/`:**

- `<especialidade>__<cliente>.json` — contrato programatico, dados estruturados.
- `<especialidade>__<cliente>.md` — facil pra Notion/email.
- `<especialidade>__<cliente>.html` — visualizacao bonita pra mostrar pro time.

### Opcao B — UI Web (para apresentar)

```bash
streamlit run app/streamlit_app.py
# abra http://localhost:8501
```

Visualmente: barra lateral pra inputs, lista ranqueada com cards, downloads em JSON/MD/CSV.

### Opcao C — API Python (para integrar)

```python
from vaipri_ref import buscar_referencias

resultado = buscar_referencias(
    handle_cliente="@clinica.exemplo",
    especialidade="dermatologia",
    modo_demo=False,  # True quando rede estiver restrita
)

for ref in resultado.referencias:
    print(ref.instagram_handle, ref.score, ref.n_anuncios_ativos)
```

---

## Modo DEMO (importante para a avaliacao)

A Meta bloqueia o IP de varios datacenters e redes corporativas para a
Biblioteca de Anuncios. Para garantir que o avaliador consiga rodar
mesmo numa rede chata, criei um **modo demo** que carrega **fixtures
sinteticas** com 3 especialidades pre-populadas (`dermatologia`,
`nutrologia`, `ortopedia`) e roda **todo o resto do pipeline real**:
matching de especialidade, score, ordenacao, relatorio.

```bash
vaipri-ref buscar @qualquercoisa dermatologia --demo
```

- Os dados na fixture sao **ficticios** — handles, nomes, numeros, tudo
  inventado para parecerem reais sem se referirem a pessoas reais.
- Cada saida em modo demo carrega um aviso explicito.
- Use `--demo` quando o objetivo for **avaliar a ferramenta**;
  use sem flag quando o objetivo for **rodar de verdade**.

Os outputs em `outputs/exemplos/` foram gerados pelo modo demo.

---

## Saidas de exemplo (3 inputs de teste)

Estao salvas em `outputs/exemplos/` e referenciadas abaixo:

| Input                                      | JSON | Markdown | HTML |
| ------------------------------------------ | ---- | -------- | ---- |
| `@clinica.exemplo` + `dermatologia`         | [json](./outputs/exemplos/dermatologia__clinica-exemplo.json) | [md](./outputs/exemplos/dermatologia__clinica-exemplo.md) | [html](./outputs/exemplos/dermatologia__clinica-exemplo.html) |
| `@nutrologo.teste` + `nutrologia`           | [json](./outputs/exemplos/nutrologia__nutrologo-teste.json)   | [md](./outputs/exemplos/nutrologia__nutrologo-teste.md)   | [html](./outputs/exemplos/nutrologia__nutrologo-teste.html)   |
| `@ortopedista.test` + `ortopedia`           | [json](./outputs/exemplos/ortopedia__ortopedista-test.json)   | [md](./outputs/exemplos/ortopedia__ortopedista-test.md)   | [html](./outputs/exemplos/ortopedia__ortopedista-test.html)   |

> Os 3 sao saidas reais do pipeline em modo demo. Para rodar de verdade
> contra a Meta, basta tirar o `--demo` da CLI.

---

## Como o pipeline funciona (1 minuto)

```
                 input: @cliente + especialidade
                              │
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │ 1. Gera ~10 termos de busca via Claude               │
   │    (dermatologia → "harmonizacao facial", "botox"…)  │
   ├──────────────────────────────────────────────────────┤
   │ 2. Meta Ad Library (scraping) por cada termo         │
   │    → lista de paginas com anuncio ativo agora        │
   ├──────────────────────────────────────────────────────┤
   │ 3. Dedup + ordena por nº de anuncios ativos          │
   │    → top ~40 candidatos                              │
   ├──────────────────────────────────────────────────────┤
   │ 4. Para cada candidato:                              │
   │    a) Resolve @ do Instagram (link FB ou Claude)     │
   │    b) Coleta metricas publicas do IG (OG meta tags)  │
   │    c) Claude classifica especialidade                │
   │    d) Calcula score 0-100 (formula transparente)     │
   ├──────────────────────────────────────────────────────┤
   │ 5. Filtra (sem anuncio? cliente? especialidade?)     │
   │ 6. Ordena por score → top 10                         │
   │ 7. Salva JSON + Markdown + HTML                      │
   └──────────────────────────────────────────────────────┘
```

Detalhes em [`docs/ARQUITETURA.md`](./docs/ARQUITETURA.md).
Trade-offs explicitos em [`docs/TRADE_OFFS.md`](./docs/TRADE_OFFS.md).

---

## Score 0–100 (extra escolhido do enunciado)

Das 3 opcoes (Score, Top 3 videos, Transcricao do hook), escolhi **Score** porque:

- E o que mais **acelera** o trabalho do analista (sabe por onde comecar).
- Os outros so fazem sentido depois que a lista existe — sao lupa, nao filtro.
- Expoe minha tese sobre "boa referencia" de forma testavel.

**Formula** (em [`src/vaipri_ref/scorer.py`](./src/vaipri_ref/scorer.py)):

```
score = 25 * f(n_ads_ativos, piso=1, teto=30)        # volume de criativos
      + 20 * f(seguidores,   piso=1k, teto=200k)     # tracao organica
      + 15 * (engajamento >= 1%)                     # nao e perfil inflado
      + 15 * (postou nos ultimos 30 dias)            # esta vivo
      + 15 * (bio menciona especialidade/CRM)        # ancora medica
      + 10 * (confianca do handle == alta)           # anti-falsa positiva
```

Quando algum dado nao esta disponivel (ex: IG bloqueado), aplico
**credito parcial** em vez de penalizar. Tudo documentado no `score_breakdown`
de cada referencia.

---

## Testes

```bash
pytest
```

71 testes cobrindo: normalizacao de inputs, parser do IG, parser da Ad
Library, scorer (limites + ordenacao), reporter (3 formatos), pipeline
end-to-end em modo demo (3 especialidades).

```
71 passed in 0.87s
```

---

## Variaveis de ambiente

| Variavel                  | Default                          | O que faz                                              |
| ------------------------- | -------------------------------- | ------------------------------------------------------ |
| `ANTHROPIC_API_KEY`       | —                                | Chave Claude. Sem ela, cai pro modo heuristico.        |
| `VAIPRI_CLAUDE_MODEL`     | `claude-haiku-4-5-20251001`      | Modelo. Haiku custa ~10x menos que Sonnet/Opus.        |
| `VAIPRI_COUNTRY`          | `BR`                             | Pais usado nos filtros da Ad Library.                  |
| `VAIPRI_MAX_CANDIDATOS`   | `40`                             | Quantos candidatos vao pra fase de enriquecimento.     |
| `VAIPRI_TOP_N`            | `10`                             | Tamanho maximo da lista final.                         |
| `VAIPRI_CACHE_DIR`        | `.cache`                         | Cache local de buscas e perfis.                        |
| `VAIPRI_HEADLESS`         | `true`                           | Playwright em modo headless. False ajuda no debug.     |
| `VAIPRI_VERBOSE`          | `false`                          | Logs detalhados.                                       |

---

## Troubleshooting

| Sintoma                                                       | Causa provavel / Solucao                                                                 |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `ERR_NAME_NOT_RESOLVED` ou `403 Forbidden` na Ad Library      | Rede bloqueando facebook.com. Rode com `--demo` ou troque para rede aberta.              |
| Metricas do IG vem todas `null`                               | Instagram bloqueia scraping anonimo. Ver `TRADE_OFFS.md` § Instagram.                    |
| `Claude API indisponivel`                                     | Falta `ANTHROPIC_API_KEY` no `.env`. A ferramenta continua, mas em modo heuristico.      |
| Lista incompleta (<10 referencias)                             | Por design — nao completamos com perfis ruins. Ver justificativa no relatorio.            |
| Playwright reclama de browser nao instalado                    | `python -m playwright install chromium`                                                  |

---

## Roadmap (V2 ideias, fora do escopo do MVP)

1. **Engajamento medido (nao estimado)** — integrar Apify ou Graph API
   Business pra ler curtidas/coments por post.
2. **Cluster de criativos** — agrupar anuncios por ancora de copy
   ("emagrecimento rapido", "antes/depois", "depoimento").
3. **Watcher continuo** — agendar buscas semanais e alertar quando um
   novo anunciante forte aparece na especialidade.
4. **Top videos + hook transcrito** — usar Whisper/Claude para
   transcrever os primeiros 5 segundos dos top videos. (Era um dos
   extras do enunciado.)
5. **Cap de custo** — limitar gasto de Claude API por execucao.

---

Construido em ~2 dias por **Joao Pedro** para a case da VaiPri (Maio/2026).

---

## Entregaveis x enunciado (checklist)

| Item pedido pelo enunciado                                  | Onde |
| ----------------------------------------------------------- | ---- |
| Doc de definicao de produto (1-2 paginas)                    | [`docs/DEFINICAO_DE_PRODUTO.md`](./docs/DEFINICAO_DE_PRODUTO.md) |
| Codigo fonte                                                 | [`src/vaipri_ref/`](./src/vaipri_ref/) |
| README explicando como rodar                                 | este arquivo |
| Output gerado para 3 inputs de teste                         | [`outputs/exemplos/`](./outputs/exemplos/) |
| Loom de ate 5 minutos                                        | [`docs/ROTEIRO_LOOM.md`](./docs/ROTEIRO_LOOM.md) (roteiro pronto para gravar) |

| Input/output pedido                                         | Onde |
| ----------------------------------------------------------- | ---- |
| @ Instagram do cliente como input                            | `pipeline.buscar_referencias(handle_cliente=…)` |
| Especialidade como input                                     | `pipeline.buscar_referencias(especialidade=…)` |
| @ Instagram da referencia                                    | `Referencia.instagram_handle` |
| Link direto pros anuncios na Biblioteca                      | `Referencia.biblioteca_anuncios_url` |
| Seguidores, engajamento, posts recentes                      | `Referencia.metricas.*` |
| Confirmacao de anuncio ativo agora                           | `Referencia.confirmacao_anuncio_ativo` |
| Quantidade de anuncios ativos                                | `Referencia.n_anuncios_ativos` |
| Nao listar perfil sem anuncio                                | `pipeline.py:110-112` |
| Nao listar perfil de outra especialidade                     | `SpecialtyMatcher` em `ai/specialty_matcher.py` |
| Lista incompleta com justificativa (nao completar com ruim)  | `Resultado.lista_incompleta` + `justificativa_lista_incompleta` |
| Extra escolhido: Score 0-100                                 | `scorer.py` + `Referencia.score_breakdown` |
