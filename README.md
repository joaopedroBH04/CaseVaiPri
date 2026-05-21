# Buscador de Referências de Tráfego Pago — VaiPri

Ferramenta que recebe **@ do Instagram + especialidade médica** e
devolve **até 10 médicos** da mesma especialidade que **rodam anúncios
ativos no Meta agora**, com métricas reais de Instagram (seguidores,
engajamento, posts), número correto de anúncios e nota 0–10 com
justificativa por critério.

**Entrega da case do Analista de Automação — Especialista em IA.**

---

## TL;DR para o avaliador

> 🚀 **Roteiro de 10 minutos**: clone → ative venv → instale → cole
> token Apify (gratuito) → rode. Detalhes em [`INSTALACAO.md`](./INSTALACAO.md).

```bash
git clone https://github.com/joaopedroBH04/CaseVaiPri.git
cd CaseVaiPri
git checkout claude/develop-case-implementation-oumwk
python3 -m venv .venv && source .venv/bin/activate    # Linux/Mac
# Windows: python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt && pip install -e .

# Cole APIFY_API_TOKEN no .env (pegue em apify.com — $5 grátis)
echo "APIFY_API_TOKEN=cole_seu_token_aqui" > .env

# Valida configuração
vaipri-ref check

# Roda
vaipri-ref buscar "@clinica.exemplo" dermatologia
```

Interface web:
```bash
streamlit run app/streamlit_app.py
```

---

## Os 5 critérios de avaliação — onde está cada um

| Critério da case                                     | Onde está                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------- |
| **1.** Definição de produto **antes** do código       | [`docs/DEFINICAO_DE_PRODUTO.md`](./docs/DEFINICAO_DE_PRODUTO.md) |
| **2.** Critério para "bom médico" — tese clara        | [`docs/DEFINICAO_DE_PRODUTO.md`](./docs/DEFINICAO_DE_PRODUTO.md) §1 |
| **3.** Funciona — entrega o esperado                  | `vaipri-ref buscar ...` + [`outputs/exemplos/`](./outputs/exemplos/) + 137 testes pytest |
| **4.** Uso estratégico de Claude Code                 | [`docs/USO_DE_CLAUDE_CODE.md`](./docs/USO_DE_CLAUDE_CODE.md) |
| **5.** Robustez — input estranho (@ inexistente etc.) | [`docs/ROBUSTEZ.md`](./docs/ROBUSTEZ.md) (53 testes específicos) |

---

## O que a ferramenta entrega (cada referência)

Conforme o enunciado, para cada referência na lista:

- ✅ **@ do Instagram** real
- ✅ **Link direto** para os anúncios na Biblioteca da Meta
- ✅ **Métricas do perfil**: seguidores, engajamento médio (real, não estimado), posts
- ✅ **Confirmação** de conta de anúncio ativa com criativos rodando agora
- ✅ **Quantidade real** de anúncios ativos (não só os do termo buscado)

E mais o **extra** (nota 0–10 com 6 critérios e justificativa visível
por referência).

## O que a ferramenta NÃO faz (regras do enunciado)

- ❌ **Não lista perfil sem anúncio ativo** (hard filter no pipeline)
- ❌ **Não lista perfil de outra especialidade** (validação por anti-keywords + matcher)
- ❌ **Não infla a lista até 10**: se só encontrar 7 bons, entrega 7 + justificativa
  explicando o que filtrou e por quê

Demonstrado em [`outputs/exemplos/nutrologia__nutrologo-teste.json`](./outputs/exemplos/nutrologia__nutrologo-teste.json),
que entrega 9 referências com justificativa por não chegar a 10.

---

## Estrutura do projeto

```
CaseVaiPri/
├── README.md                        ← você está aqui
├── INSTALACAO.md                    ← guia passo a passo (10 min)
├── docs/
│   ├── DEFINICAO_DE_PRODUTO.md      ← TESE (escrita antes do código)
│   ├── ARQUITETURA.md               ← decisões técnicas
│   ├── TRADE_OFFS.md                ← autocrítica + limites
│   ├── USO_DE_CLAUDE_CODE.md        ← como usei Claude Code estrategicamente
│   ├── ROBUSTEZ.md                  ← cobertura de inputs estranhos
│   └── COMO_ATIVAR_DADOS_REAIS.md   ← tutorial Apify (gratuito)
├── src/vaipri_ref/                  ← código-fonte (~5150 linhas)
│   ├── pipeline.py                  ← orquestrador (7 etapas)
│   ├── discovery/                   ← Apify Ad Library + Graph + scraping
│   ├── instagram/                   ← Apify IG + heurística de handle
│   ├── ai/                          ← Claude wrapper + classificador
│   ├── scorer.py                    ← nota 0-10 com 6 critérios
│   ├── reporter.py                  ← JSON, Markdown, HTML
│   └── cli.py                       ← `vaipri-ref` commands
├── app/streamlit_app.py             ← interface web
├── outputs/exemplos/                ← 3 inputs de teste pré-gerados
└── tests/                           ← 137 testes pytest (todos verdes)
```

---

## Como rodar — resumo

| Cenário                                          | Comando                                                      |
| ------------------------------------------------ | ------------------------------------------------------------ |
| Validar instalação                                | `vaipri-ref check`                                           |
| Busca real com Apify (recomendado)                | `vaipri-ref buscar "@x" dermatologia`                        |
| Busca em modo demo (fixtures sintéticas)         | `vaipri-ref buscar "@x" dermatologia --demo`                 |
| Interface web                                     | `streamlit run app/streamlit_app.py`                         |
| Rodar testes                                      | `pytest`                                                     |
| Limpar cache (forçar busca fresca)                | `vaipri-ref limpar-cache`                                    |
| Ver todos os comandos                             | `vaipri-ref --help`                                          |

> ⚠️ No **Windows PowerShell**, sempre coloque o `@cliente` entre **aspas**:
> `vaipri-ref buscar "@clinica.exemplo" dermatologia`. Sem aspas, o PowerShell
> interpreta o `@` como operador especial e dá erro.

---

## Configuração de chaves de API

| Chave              | Obrigatória? | Custo            | Tutorial                                                  |
| ------------------ | :----------: | ---------------- | --------------------------------------------------------- |
| `APIFY_API_TOKEN`  | **SIM**      | **$0** ($5 grátis) | [`docs/COMO_ATIVAR_DADOS_REAIS.md`](./docs/COMO_ATIVAR_DADOS_REAIS.md) |
| `META_ACCESS_TOKEN`| Opcional     | $0               | Cabe se app passar por App Review da Meta (não recomendo) |
| `ANTHROPIC_API_KEY`| Opcional     | $5+              | Melhora qualidade do match (não necessário pra rodar)     |

Detalhes completos em [`INSTALACAO.md`](./INSTALACAO.md) e
[`docs/COMO_ATIVAR_DADOS_REAIS.md`](./docs/COMO_ATIVAR_DADOS_REAIS.md).

---

## Saídas de exemplo (3 inputs de teste)

Arquivos já gerados em [`outputs/exemplos/`](./outputs/exemplos/), em
3 formatos (JSON estruturado, Markdown legível, HTML estilizado):

| Input                                       | Especialidade  | Resultado                          |
| ------------------------------------------- | -------------- | ---------------------------------- |
| `@clinica.exemplo`                           | dermatologia   | 10 referências                     |
| `@nutrologo.teste`                           | nutrologia     | **9 referências + justificativa** (mostra que cumpre a regra) |
| `@ortopedista.test`                          | ortopedia      | 10 referências                     |

---

## Como o pipeline funciona (visão geral)

```
Input: @cliente + especialidade
   │
   ▼
[1] Gera termos de busca contextuais (curados + IA)
[2] Busca na Ad Library (Apify → Graph API → scraping)
[3] Dedup + ranqueia preliminar (top 40)
[4] CONTAGEM REAL de anúncios via Apify (1 chamada batch)
[5] Para cada candidato:
    a. Resolve handle do Instagram
    b. Enriquece com Apify IG (seguidores, engajamento real, posts)
    c. Filtra anti-keywords (marca, drogaria, etc.)
    d. Valida especialidade
    e. Calcula nota 0-10 com 6 critérios
[6] Filtra hard-rules + ordena + corta top 10
[7] Salva JSON + Markdown + HTML
```

Detalhes técnicos em [`docs/ARQUITETURA.md`](./docs/ARQUITETURA.md).

---

## Stack

- **Python 3.10+** com Pydantic, Typer, Rich
- **Apify Platform** para Ad Library + Instagram (substitui scraping)
- **Streamlit** para interface web
- **diskcache** para cache local (não persiste entre runs sensíveis)
- **httpx + tenacity** para HTTP robusto
- **pytest** para 137 testes automatizados

---


---

## Autoria

Construído em ~2 dias por **João Pedro** para a case da VaiPri (Maio/2026).

**Sobre o uso de Claude Code:** o documento [`docs/USO_DE_CLAUDE_CODE.md`](./docs/USO_DE_CLAUDE_CODE.md)
detalha como usei a ferramenta em **planejamento** (3 docs antes de qualquer
linha de código), **debugging** (3 bugs reais caçados com diagnóstico próprio
+ correção assistida), **refatoração** (3 casos) e como **componente em runtime**
(opcional, melhora match). O raciocínio de produto, a tese de "bom médico",
o score, os pesos e os anti-critérios são meus — defendo cada decisão.
