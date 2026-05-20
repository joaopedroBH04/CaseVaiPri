# Definição de produto — Buscador de Referências de Tráfego Pago

> Documento escrito **antes do código**, como o enunciado pede.
> Aqui está a tese; o "como" técnico fica em [`ARQUITETURA.md`](./ARQUITETURA.md)
> e os trade-offs em [`TRADE_OFFS.md`](./TRADE_OFFS.md).

---

## 1. Definição de "bom médico de referência"

Uma referência é boa quando o time de tráfego consegue extrair **insumo
direto** dela: criativo, ângulo de copy e oferta que dê para adaptar
para o cliente novo. Pra isso acontecer, o perfil precisa cumprir
**três condições obrigatórias** e somar **cinco sinais de qualidade**.

### Condições obrigatórias (eliminatórias)

| Condição                  | Por quê                                                                  |
| ------------------------- | ------------------------------------------------------------------------ |
| **Anúncio ativo agora**   | Sem ad rodando hoje, não há criativo pra observar. Hard filter.          |
| **Mesma especialidade**   | Dermato não inspira campanha de ortopedia. Ângulo de copy não bate.      |
| **Perfil público no IG**  | Sem perfil público, não dá pra cruzar com posicionamento orgânico.       |

> Se qualquer uma falha, descarto. Não importa quão grande seja o perfil.

### Sinais de qualidade (compõem a nota 0–10)

| Sinal                          | Peso | Por que importa                                                                 |
| ------------------------------ | :--: | ------------------------------------------------------------------------------- |
| **Volume de anúncios rodando** | 2,5  | Mais criativos = mais aprendizado pra copiar. Piso 1, teto 30.                  |
| **Tração no Instagram**         | 2,0  | Seguidores `≥ 1k`; teto 200k. Validar audiência consolidada.                    |
| **Engajamento real**            | 1,5  | `(likes + comentários) ÷ seguidores ≥ 1%` pra filtrar perfil inflado.           |
| **Perfil ativo**                | 1,5  | Postou nos últimos 30 dias. Quem investe em ads e abandonou o feed = funil ruim. |
| **Identidade médica clara**     | 1,5  | Bio menciona especialidade, CRM ou RQE. Filtra coach/influencer.                |
| **Confiabilidade do match**     | 1,0  | Quão certo estou de que aquele @ é mesmo do médico (anti-falso-positivo).        |

A nota final vira um rótulo humano: **8,5+ Excelente · 7,0+ Muito boa
· 5,5+ Boa · 4,0+ Razoável · <4 Fraca**.

### Anti-critérios (o que NÃO é referência boa)

Mesmo cumprindo as 3 obrigatórias, descarto perfis que são:

- **Marcas/lojas/cosméticos** (SkinCeuticals, BEYOUNG, Anna Pegova): anúncios
  rolam, mas o conteúdo é institucional. Não serve de referência individual.
- **Drogarias e farmácias** (Drogaria São Paulo): mesma lógica.
- **Hospital ou rede multi-especialidade**: criativo institucional, não capta lead direto.
- **Influencer/coach sem CRM**: não é médico, ângulo de copy é outro.
- **Perfil novo (< 3 meses) com muitos ads**: alto risco de ser dropshipper de saúde.

> Detecto isso por anti-keywords (`drogaria`, `cosmetic`, `loja oficial`...),
> nome em CAPS sem `Dr/Dra`, e bio com indícios de marca (`linha`, `kit`,
> `compre`, `frete grátis`...).

---

## 2. Estratégia de busca

Começo pela **Biblioteca de Anúncios da Meta**, não pelo Instagram.
Razão: ela já filtra `anúncio_ativo = true` de graça. Buscar no IG
primeiro seria 10× mais trabalho pra chegar no mesmo conjunto.

**Fluxo em 5 passos:**

```
Input: @cliente + especialidade
   │
   ▼
[1] Brainstorm de termos de busca (curados + IA)
    ex: "dermatologia" → ["dermatologista", "harmonização facial",
        "botox", "preenchimento labial", "melasma", "acne", ...]
   │
   ▼
[2] Para cada termo, consulta Meta Ad Library (pais=BR, status=ativo)
    via 3 caminhos em cascata:
    • Apify Facebook Ads Library Scraper (preferido — dados completos)
    • Meta Graph API oficial (se App estiver verificado)
    • Scraping HTTP (último fallback)
   │
   ▼
[3] Deduplica por page_id, ranqueia preliminarmente por nº de ads
    → top 40 candidatos
   │
   ▼
[4] CONTAGEM REAL via Apify: 1 chamada batch que pega o TOTAL
    real de anúncios ativos por página (não só os que mencionam
    o termo buscado). Garante que o número bate com o que aparece
    na Ad Library da Meta.
   │
   ▼
[5] Para cada candidato:
    a. Resolve handle do Instagram (link FB, hint Apify ou heurística)
    b. Enriquece com Apify IG: seguidores, engajamento real, posts
    c. Valida especialidade (anti-keywords + termo origem + heurística IA)
    d. Calcula nota 0-10 com breakdown justificável
    e. Descarta o próprio cliente da lista
   │
   ▼
[6] Filtra hard-rules + ordena por nota → top 10 (ou menos com justificativa)
```

**Por que esta ordem funciona:**

- Começar pela Ad Library elimina o problema "10k perfis no IG, quem anuncia?".
- A camada de **anti-keywords** + **bio do Apify** filtra marcas/drogarias que
  aparecem em buscas por termos médicos mas não servem como referência.
- A **contagem real via Apify** garante que o número na minha tabela bate
  com o número que aparece na Biblioteca de Anúncios quando o avaliador
  clica no link.
- Se a especialidade for rara e eu não achar 10 perfis bons, entrego **N
  com justificativa** — exatamente o que o enunciado pede.

---

## 3. Outcome esperado

> **Em uma frase:** o que hoje toma **4 a 6 horas** de analista por
> cliente novo (abrir Biblioteca, pesquisar nome por nome, validar IG,
> anotar em planilha) passa a tomar **3 a 5 minutos** — o tempo de
> rodar a ferramenta — devolvendo 10 referências já filtradas,
> ranqueadas e com link direto para cada coleção de anúncios.

**Economia agregada:** assumindo ~20 onboardings/mês × 5h economizadas
= **100h/mês de analista liberadas** para tarefas de maior valor
(análise de criativo, briefing de roteiro, otimização de campanha).

---

## Anti-escopo (o que **não** vou resolver agora)

Cortes conscientes pro MVP:

- **Não** classifica criativos por ângulo de copy automaticamente — o
  analista ainda assiste aos vídeos. Possível V2.
- **Não** monitora ao longo do tempo — é busca pontual, não watcher.
- **Não** sugere copy pronta — entrega referências, não criativo final.
- **Não** cruza com performance real (CPL, CTR) — dado privado, não
  está na Biblioteca.

Esses 4 cortes são intencionais: prefiro entregar **uma coisa redonda**
em 2-3 dias do que 5 coisas pela metade.
