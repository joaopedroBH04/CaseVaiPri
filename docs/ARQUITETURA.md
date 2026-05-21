# Arquitetura — Buscador de Referências

Documento técnico para quem vai ler o código. Para "o porquê" do
produto, ver [`DEFINICAO_DE_PRODUTO.md`](./DEFINICAO_DE_PRODUTO.md).

## Visão geral

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERFACES                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐    │
│  │   CLI       │   │  Streamlit  │   │  Python API         │    │
│  │   (typer)   │   │   (web UI)  │   │  (programmatic)     │    │
│  └─────────────┘   └─────────────┘   └─────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PIPELINE                                  │
│                                                                 │
│   buscar_referencias(handle_cliente, especialidade)             │
│                                                                 │
│   1. SearchTermsGenerator  ──── usa Claude API                  │
│   2. MetaAdLibraryScraper  ──── Playwright + fallback HTTP      │
│   3. CandidateAggregator   ──── dedup + score inicial           │
│   4. InstagramEnricher     ──── métricas públicas               │
│   5. SpecialtyMatcher      ──── valida com Claude               │
│   6. Scorer                ──── 0-10 (extra do case)            │
│   7. Reporter              ──── JSON + Markdown + HTML          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FONTES DE DADOS                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │ Meta Ad Library  │  │   Instagram      │  │  Claude API  │   │
│  │ (Playwright)     │  │   (público + IA) │  │  (Anthropic) │   │
│  └──────────────────┘  └──────────────────┘  └──────────────┘   │
│           │                       │                  │          │
│           └────── Cache Layer ────┴──────────────────┘          │
│                  (disco/JSON, TTL 24h)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Decisões de stack

| Decisão                        | Por quê                                                                |
| ------------------------------ | ---------------------------------------------------------------------- |
| **Python 3.11+**               | Ecossistema de scraping + IA maduro, tipagem boa pra projeto sério.    |
| **Playwright (Chromium)**      | Meta Ad Library é JS-heavy. Selenium é mais frágil; httpx puro não pega o conteúdo dinâmico. |
| **httpx (async)**              | Para IG público e Claude API. Mais rápido e moderno que `requests`.    |
| **Pydantic v2**                | Validação dos modelos de saída. Garante contrato estável.              |
| **Typer + Rich**               | CLI moderna com saída bonita. Ajuda no demo ao vivo.                   |
| **Streamlit**                  | UI web em <100 linhas que parece produto. Fácil de demonstrar.         |
| **Anthropic SDK (Claude)**     | Para *specialty matching*, geração de termos de busca e justificativas. |
| **diskcache**                  | Cache local em disco. Rerodar busca não custa nada.                    |

**Por que não:**

- **Selenium/Puppeteer Python** — Playwright é melhor mantido em 2026.
- **Scrapy** — overkill, e a Ad Library requer JS de qualquer forma.
- **FastAPI + frontend React** — leva 3x o tempo do Streamlit pra mesma demo.
- **Banco SQL** — não há estado persistente entre runs.

## Estrutura do código

```
src/vaipri_ref/
├── __init__.py            # exporta API pública
├── config.py              # carrega .env, valida chaves
├── models.py              # Pydantic: Referencia, Anuncio, Metricas, Resultado
├── pipeline.py            # orquestra os 7 passos
├── cli.py                 # entrada Typer
├── reporter.py            # JSON/MD/HTML
├── scorer.py              # score 0-10 (extra)
│
├── discovery/
│   ├── search_terms.py    # Claude → lista de termos
│   └── meta_ad_library.py # Playwright scraper
│
├── instagram/
│   └── scraper.py         # async httpx + parsing OG metadata
│
├── ai/
│   ├── claude_client.py   # wrapper fino do SDK
│   └── specialty_matcher.py
│
└── utils/
    ├── cache.py           # diskcache wrapper
    ├── normalize.py       # @ → handle puro, etc.
    └── logger.py          # rich logger
```

## Fluxo detalhado de uma busca

Para `python -m vaipri_ref buscar @clinica.exemplo dermatologia`:

1. **`config.load()`** — lê `.env`, valida `ANTHROPIC_API_KEY`.
2. **`SearchTermsGenerator.gerar("dermatologia")`** — chama Claude com
   prompt curado, recebe ~10 termos em pt-BR.
3. **`MetaAdLibraryScraper.buscar(termos)`** — para cada termo, tenta
   em ordem:
   a. **Graph API oficial** (`graph.facebook.com/v19.0/ads_archive`)
      se `META_ACCESS_TOKEN` está configurado. **Caminho recomendado**
      pra dados reais — funciona em qualquer rede, retorna JSON limpo.
   b. **Scraping HTTP** da UI pública (fallback rápido).
   c. **Scraping Playwright** (fallback final, frágil).
   Extrai `(page_id, page_name, page_url, ig_handle_hint, n_anuncios_ativos)`.
4. **`CandidateAggregator.dedup(candidatos)`** — agrupa por `page_id`,
   soma n_anuncios, ordena.
5. **`InstagramEnricher.enriquecer(candidato)`** — resolve @ do IG
   (via link na FB Page ou via inferência Claude se faltar), busca
   página pública do IG, extrai meta tags Open Graph + Twitter Cards
   (resultado: `seguidores`, `posts_publicos`, `bio`). Se não der,
   marca como `indisponivel: true` e segue.
6. **`SpecialtyMatcher.confirmar(referencia, "dermatologia")`** — passa
   bio + nome + nome do site para Claude com prompt de classificação.
   Retorna `bool` + `confianca` + `justificativa`.
7. **`Scorer.calcular(referencia)`** — aplica fórmula transparente
   (ver `scorer.py`). Resultado 0–10 (decisão consciente vs case que
   pede 0–100; ver `TRADE_OFFS.md §5`).
8. **Filtros finais:** descarta cliente, descarta especialidade errada,
   descarta sem anúncio ativo. Ordena por score, corta em 10.
9. **`Reporter.salvar(...)`** — gera `outputs/<especialidade>.json`,
   `outputs/<especialidade>.md` e `outputs/<especialidade>.html`.

## Erros e edge cases

- **`@` que não existe no Instagram** — pipeline segue; só não enriquece
  métricas. Se for o cliente, vira warning no relatório.
- **Especialidade rara (ex: "neuro-pediatria")** — Claude gera termos
  específicos; se Ad Library devolve <10 resultados, ferramenta entrega
  N com `justificativa_lista_incompleta`.
- **Bloqueio da Meta** — Playwright detecta tela de login/captcha,
  cai pro fallback de HTTP direto na URL pública (que ainda devolve
  parte dos dados via JSON embedded em `<script>`).
- **IG público bloqueado** — usa Claude para inferir `seguidores` por
  faixa (ex: 10k–50k) a partir de menções em outros lugares, e marca
  o campo como `estimado: true`. Transparência.
- **Sem chave Claude** — ferramenta ainda roda, mas pula
  `SpecialtyMatcher`. Os resultados saem com flag `validado_manualmente_pendente`.

Ver [`TRADE_OFFS.md`](./TRADE_OFFS.md) para a discussão completa de
limitações e por que cada escolha foi feita.
