# Defesa na reunião — respostas em 60 segundos

> Cheat sheet pra reler 5 minutos antes da reunião. Cada bloco é uma
> resposta de **30 a 60 segundos** para uma pergunta provável do
> avaliador. Mais profundidade nos docs apontados.

---

## Pergunta provável 1 — "Como você decidiu o que é uma 'boa referência'?"

**Resposta direta (45s):**

> Escrevi a tese **antes** de qualquer linha de código, em
> `docs/DEFINICAO_DE_PRODUTO.md`. Uma boa referência precisa de
> **três condições obrigatórias** (anúncio ativo agora, mesma
> especialidade, perfil público no IG) e somar **cinco sinais de
> qualidade** ponderados no score de 0 a 10. Também defini
> **anti-critérios**: marcas, drogarias, hospital, influencer sem
> CRM. A lógica está no `pipeline.py` e no `scorer.py`, e os pesos
> estão justificados em `TRADE_OFFS.md` §5.

---

## Pergunta provável 2 — "Por que esses pesos no score?"

**Resposta direta (40s):**

> Volume de anúncios pesa **2,5** porque é o ativo central que importa
> pro time de tráfego — mais criativos = mais aprendizado pra copiar.
> Seguidores pesam **2,0**, menos que volume, porque "muito seguidor
> + zero ad" não vale nada pro caso de uso. Engajamento real (1,5),
> perfil ativo (1,5) e bio médica (1,5) garantem que o perfil tá
> vivo e é médico de verdade. Confiança no handle (1,0) é o anti-falsa
> positiva. Total = 10. Fórmula transparente em `scorer.py:47-107`.

---

## Pergunta provável 3 — "E se não encontrar 10? Vai inflar a lista?"

**Resposta direta (30s):**

> Não. Hard-coded em `pipeline.py:398-408`: se filtrar menos de N
> bons, o `Resultado.lista_incompleta=True` sai com `justificativa`
> explicando quantos foram brutos, quantos filtrados por especialidade,
> quantos sem anúncio ativo. **O exemplo `nutrologia__nutrologo-teste.json`
> mostra isso ao vivo: entrega 9 + painel vermelho.** É exatamente
> o que o enunciado pede.

---

## Pergunta provável 4 — "Como usou Claude Code? Foi só pedir código?"

**Resposta direta (50s):**

> Não. Documentado em `docs/USO_DE_CLAUDE_CODE.md` com 4 frentes:
>
> 1. **Planejamento** (3 docs escritas antes do código): debate de tese,
>    estratégia de busca, anti-escopo.
> 2. **Debugging** (3 bugs reais que **eu** cacei): parser numérico
>    pt-BR vs en, vazamento entre cards da Ad Library, hospital
>    passando heurística. Cada um tem regression test no `tests/`.
> 3. **Refatoração** (3 casos): dedup do pipeline, separação cache/lógica
>    no handle_resolver, ordem das helpers no Streamlit.
> 4. **Claude como componente do produto em runtime**: geração de termos,
>    match de especialidade, inferência de handle. Não só durante o dev.
>
> **O score, os pesos e a tese são meus** — Claude refinou redação,
> não conceito.

---

## Pergunta provável 5 — "E robustez? Input estranho?"

**Resposta direta (40s):**

> 53 testes específicos de robustez em `test_robustez.py` +
> `test_normalize.py` + `test_ig_parser.py` + `test_ad_library_parser.py`.
> Cobre os 3 casos do enunciado:
>
> - **`@` inválido** → ValueError com mensagem clara, antes de qualquer
>   chamada externa. Reproduzível: `vaipri-ref buscar @@ dermatologia --demo`
> - **Especialidade rara** → fallback de termos curados; se Ad Library
>   devolve <10, sai com `lista_incompleta` + justificativa
> - **Perfil sem anúncio** → filtrado em `pipeline.py:252-254`, sem
>   chamar Claude nem IG (economia + correção)
>
> Detalhe completo em `docs/ROBUSTEZ.md`.

---

## Pergunta provável 6 — "Por que tantos fallbacks (Apify, Graph API, scraping)?"

**Resposta direta (45s):**

> Cada fonte tem trade-offs reais documentados em `docs/TRADE_OFFS.md` §1:
>
> - **Apify** (recomendado) — dados completos, $0 no free tier (~$0.50/busca),
>   resolve métricas reais do IG que outros caminhos não pegam
> - **Graph API oficial** — gratuita mas precisa App Review pra produção;
>   em Dev Mode da Meta dá rate limit baixo
> - **Scraping HTTP/Playwright** — último fallback, Meta bloqueia IPs
>   de datacenter
>
> Cascata garante que **a ferramenta sempre roda em alguma fonte**.
> Modo `--demo` cobre o caso de avaliador em rede restrita.

---

## Pergunta provável 7 — "O que ficou faltando? Autocrítica?"

**Resposta direta (40s):**

> 5 dívidas conscientes documentadas em `TRADE_OFFS.md §6`:
>
> 1. **Engajamento é estimado**, não medido (IG bloqueia sem login)
> 2. Não validei com especialidade muito rara (ex: geriatria integrativa)
> 3. Não há replay idempotente (Ad Library reordena entre runs)
> 4. Custo de Claude não tem cap de orçamento
> 5. `--limit` de candidatos é fixo em 40, não parametrizado
>
> Cortei 4 features de propósito pra entregar **uma coisa redonda em
> 2-3 dias**: classificação de criativo, monitoramento contínuo, geração
> de copy, cruzamento com performance real. Listadas em "Anti-escopo"
> de `DEFINICAO_DE_PRODUTO.md`.

---

## Pergunta provável 8 — "Como escalaria pra produção?"

**Resposta direta (30s):**

> Três frentes:
>
> 1. **Apify → IG Graph API Business** (login real, métricas exatas)
> 2. **Snapshot diário** de cada query pra ter histórico (eliminaria a
>    não-determinismo)
> 3. **Worker assíncrono + fila** (hoje pipeline é síncrono; pra 100+
>    buscas/dia, joga em RabbitMQ ou similar)
>
> Custo estimado em produção: ~$0.50/busca, ~$15/dia em 30 onboardings.
> Vale pelo ROI: 100h/mês de analista liberadas (cálculo em
> `DEFINICAO_DE_PRODUTO.md §3`).

---

## Resumo dos 5 critérios — onde cada um está

| Critério                               | Doc principal                                   |
| -------------------------------------- | ----------------------------------------------- |
| 1. Definição de produto                 | `docs/DEFINICAO_DE_PRODUTO.md`                  |
| 2. Tese de "bom médico"                  | `docs/DEFINICAO_DE_PRODUTO.md` §1               |
| 3. Funciona                             | `outputs/exemplos/` + 137 testes pytest         |
| 4. Uso estratégico de Claude Code        | `docs/USO_DE_CLAUDE_CODE.md`                    |
| 5. Robustez                              | `docs/ROBUSTEZ.md` + `tests/test_robustez.py`   |

---

## Comandos que rolam ao vivo na reunião (se pedir demo)

```bash
# Validar saúde do projeto (8s):
pytest                                                  # 137 passed

# Caso normal: dermatologia, deve dar 10:
vaipri-ref buscar @clinica.exemplo dermatologia --demo

# Caso "lista incompleta": nutrologia, deve dar 9 + justificativa:
vaipri-ref buscar @nutrologo.teste nutrologia --demo

# Robustez: handle inválido, deve dar ValueError:
vaipri-ref buscar @@ dermatologia --demo

# UI:
streamlit run app/streamlit_app.py
```

---

## Frases de defesa que funcionam

- *"O raciocínio é meu, o Claude refinou redação."*
- *"Esse corte é proposital — está em anti-escopo, defendo a decisão."*
- *"O score é uma heurística informada, não modelo treinado — é boa pra
  ranquear, não pra garantir 100%."*
- *"Em produção eu trocaria por X, está em TRADE_OFFS §6."*
- *"Esse é exatamente o caso que o enunciado pede: entrega N + justificativa."*

---

**Antes de entrar na reunião:**

1. Reler este arquivo (5 min)
2. Reler `DEFINICAO_DE_PRODUTO.md` §1 (3 min)
3. Reler `USO_DE_CLAUDE_CODE.md` §1-2 (3 min)
4. Abrir um terminal com `(.venv)` ativo, pronto pra `pytest` ou `vaipri-ref buscar` se pedirem demo ao vivo.
