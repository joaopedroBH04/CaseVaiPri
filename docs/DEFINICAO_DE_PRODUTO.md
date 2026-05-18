# Definição de Produto — Buscador de Referências de Tráfego Pago

> Documento curto, escrito **antes** do código, conforme pedido no enunciado.
> Aqui está o "porquê" da ferramenta. O "como" técnico fica em
> [`ARQUITETURA.md`](./ARQUITETURA.md) e os trade-offs em
> [`TRADE_OFFS.md`](./TRADE_OFFS.md).

---

## 1. Definição de "bom médico de referência"

Uma referência é **boa** quando o time de tráfego consegue extrair
**insumo direto** dela: criativo, ângulo de copy e estrutura de oferta
que dá pra adaptar para o cliente novo. Em termos práticos, isso só
acontece quando o perfil cumpre **três condições obrigatórias** e
acumula sinais de **qualidade**:

### Condições obrigatórias (eliminatórias)

| Condição                  | Por quê                                                                  |
| ------------------------- | ------------------------------------------------------------------------ |
| **Anúncio ativo agora**   | Sem ad rodando hoje, não há criativo pra observar. Hard filter.          |
| **Mesma especialidade**   | Dermato não inspira campanha de ortopedista. Ângulo de copy não bate.    |
| **Perfil público no IG**  | Sem perfil público, não dá pra cruzar com posicionamento orgânico.       |

> Se qualquer uma falha, o perfil é descartado — não importa quão grande seja.

### Sinais de qualidade (somam pontos no score)

Uma referência **muito** boa, além de cumprir os hard filters, tem:

1. **Volume de criativos rodando** — quem testa muito, gera mais
   aprendizado pra copiar. `n_anuncios_ativos >= 3` é o piso saudável.
2. **Conta com tração orgânica** — `seguidores >= 5.000` e postagens
   nos últimos 30 dias. Quem investe em mídia paga mas abandonou o
   feed costuma ter funnel quebrado e referência ruim de copy.
3. **Engajamento real** — taxa de engajamento estimada `>= 1%` nos
   últimos posts (curtidas + comentários ÷ seguidores). Filtra perfil
   inflado por seguidores comprados.
4. **Posicionamento médico claro** — bio menciona a especialidade,
   CRM e/ou número de registro profissional. Filtra coach, influencer
   genérico ou clínica multi-especialidade que não serve de referência
   focada.
5. **Há mais de 6 meses anunciando** (proxy: variações de criativo) —
   indica que o funil já foi otimizado, não é teste inicial.

Esses cinco sinais viram **score 0–100**. Lista entra ordenada por score.

### O que **não** é referência boa (anti-critérios)

- Perfil com 1M de seguidores mas 0 anúncios ativos → influencer, não anunciante.
- Perfil de marca de produto (cosmético, suplemento) que vende para médico → B2B, não serve.
- Página de hospital ou rede de clínicas multi-especialidade → criativo institucional, não capta lead.
- Perfil novo (< 3 meses) com muitos anúncios → pode ser dropshipper de saúde, alto risco.

---

## 2. Estratégia de busca

A busca **começa pela Biblioteca de Anúncios da Meta**, não pelo
Instagram. Razão: é a fonte que já filtra `anúncio_ativo = true` de
graça. Buscar primeiro no Instagram e depois validar anúncio na Meta
seria fazer 10x mais trabalho.

**Fluxo em 5 passos:**

```
Input: @cliente + especialidade
   │
   ▼
[1] Brainstorm de termos de busca (Claude API)
    ex: "dermatologia" → ["dermatologista", "dermato",
        "tratamento de pele", "harmonização facial", "botox",
        "preenchimento", "limpeza de pele", "acne", "melasma", ...]
   │
   ▼
[2] Para cada termo, consulta Meta Ad Library
    (filtro: país=BR, status=ativo)
    → coleta lista de páginas anunciantes
   │
   ▼
[3] Deduplica páginas e ranqueia por nº de anúncios ativos
    → top ~40 candidatos
   │
   ▼
[4] Para cada candidato:
    a. Resolve handle do Instagram (link na página FB ou inferência IA)
    b. Coleta métricas públicas do IG (seguidores, posts recentes, engaj.)
    c. Valida especialidade com Claude (lê bio + 3 últimos posts)
    d. Exclui o próprio cliente da lista
   │
   ▼
[5] Filtra hard-rules + ordena por score → devolve top 10 (ou menos)
```

**Por que esse fluxo:**

- Começar pela Meta Ad Library evita o problema "10k perfis no IG, qual
  anuncia?". Já partimos do conjunto que anuncia.
- Brainstorm com IA cobre sinônimos e nichos da especialidade (ex:
  "dermato" pega "dermatologia estética", "tricologia", "dermato clínica").
- Validação de especialidade com IA (não regex) tolera bio criativa,
  emoji e variação linguística.
- Score na saída permite **entregar menos de 10 se a especialidade
  for rara** — exatamente o que o enunciado pede.

---

## 3. Outcome esperado

> **Uma frase:** o que hoje toma **4 a 6 horas** de analista por
> cliente novo (abrir Biblioteca, pesquisar, validar IG, anotar em
> planilha) passa a tomar **3 a 5 minutos** — o tempo de rodar a
> ferramenta — devolvendo um bloco de 10 referências já filtradas,
> ranqueadas e com link direto pros criativos.

**Economia agregada:** assumindo ~20 onboardings/mês × 5h economizadas
= **100h/mês de analista liberadas** para tarefas de maior valor
(análise de criativo, briefing de roteiro, otimização de campanha).

---

## Anti-escopo (o que **não** vamos resolver agora)

Decisões conscientes do MVP:

- **Não** classifica criativos por ângulo de copy automaticamente — o
  analista ainda assiste aos vídeos. Possível V2.
- **Não** monitora ao longo do tempo — é uma busca pontual, não um
  watcher.
- **Não** sugere copy pronta — entrega referências, não criativo final.
- **Não** cruza com performance real do anunciante (CPL, CTR) — esses
  dados são privados e não estão na Biblioteca.

Esses cortes são intencionais: melhor entregar 1 coisa redonda em 2
dias do que 5 coisas pela metade.
