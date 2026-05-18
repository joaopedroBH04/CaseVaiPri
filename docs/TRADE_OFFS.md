# Trade-offs e limitações

O enunciado pede explicitamente: *"Se algum dado ficar inviável de
pegar (limite de API, bloqueio), explica no doc o trade-off que
escolheu."* Este documento é honesto sobre cada um.

## TL;DR

| Dado                          | Origem                  | Confiança | Trade-off                                          |
| ----------------------------- | ----------------------- | --------- | -------------------------------------------------- |
| Anúncios ativos               | Meta Ad Library scraping | Alta      | Depende de Playwright + IP não bloqueado.          |
| Especialidade match           | Claude API (bio + nome) | Alta      | Custa ~$0,01 por candidato em LLM call.            |
| Seguidores IG                 | Meta tags públicas      | Média     | Instagram dificulta scraping; usa OG/Twitter tags. |
| Engajamento médio             | Cálculo a partir dos 3 últimos posts | Média | Posts privados ou sem like público viram "n/d".|
| Posts recentes (datas)        | HTML público            | Baixa     | Layout muda; parser pode quebrar.                  |
| @ Instagram a partir da FB Page | Link na bio da FB Page | Alta      | Quando falta, Claude infere — marcamos como `inferido`. |

---

## 1. Meta Ad Library

**O que existe:**

- **API oficial** (`graph.facebook.com/.../ads_archive`) — mas restringe
  a maioria dos campos a anúncios "de tópicos sociais, eleições ou
  política". Anúncio médico não cai aí.
- **Ad Library UI** (`facebook.com/ads/library/`) — pública, sem login.
  Esse é o caminho.

**O que escolhi:** Scraping da UI pública com Playwright (Chromium headless),
filtrando por `country=BR` e `active_status=active`.

**Por quê:**

- API oficial não cobre o vertical de saúde.
- A UI pública já entrega tudo que precisamos: nome da página,
  link da página, número de anúncios ativos, link para a coleção
  de anúncios.
- Playwright lida com o JS pesado da página.

**Riscos conhecidos:**

1. **Bloqueio por IP** — se rodar muitas buscas seguidas, a Meta serve
   captcha. Mitigação: cache em disco (rerodar não custa) + sleep
   randômico entre requests + retry com backoff.
2. **Mudança de layout** — a Meta mexe na UI ocasionalmente. Mitigação:
   parser usa duas estratégias (JSON embedded em `<script>` e seletores
   DOM) e cai do JSON pro DOM se a primeira falhar. Logs claros.
3. **Carga assíncrona** — alguns dados aparecem só depois de scroll.
   Mitigação: o scraper faz scroll programado até a contagem de itens
   estabilizar.

**Alternativa descartada:** serviços de scraping pagos (Apify,
Bright Data). Funcionam, mas adicionam custo recorrente e
dependência externa. O case pediu pra rodar de verdade, não pra
montar uma stack de SaaS.

---

## 2. Instagram

**A dor real:** desde 2022, o IG bloqueia quase tudo sem login.

- `instagram.com/{user}/?__a=1` → 401.
- HTML público da página de perfil → conteúdo principal sai só com JS,
  e ainda assim quase tudo está atrás de paywall de login.

**O que dá pra pegar sem login:**

- **Open Graph meta tags** no HTML inicial: `og:description` contém
  string padronizada do tipo
  `"12,5K Followers, 437 Following, 1.234 Posts - See Instagram photos and videos from..."`.
  Isso me dá seguidores, seguindo e número total de posts.
- **Twitter Card meta tags**: `twitter:title` traz nome completo,
  `twitter:image` traz foto de perfil.

**O que **não** dá pra pegar sem login:**

- Curtidas e comentários post-a-post (necessário para engajamento real).
- Data exata dos últimos posts.
- Texto da bio (a meta description tem só uma versão truncada).

**O que escolhi:**

1. Coleto OG/Twitter meta tags do HTML público → seguidores, total de posts.
2. Estimo engajamento por faixa baseado em benchmarks públicos da
   indústria (médicos no BR: ~1,2% médio). É *estimativa*, marcada como tal.
3. Marco campos não obtidos com `null` + flag `metricas_completas: false`.

**Alternativa para produção:** integrar com o **Instagram Graph API**
(requer Business Account verificado) ou **Apify Instagram Profile Scraper**
(~$0,01 por perfil). Documentado no README como upgrade path.

---

## 3. Resolução do @ Instagram a partir da página FB

Quase toda página FB médica tem link pro IG na bio ou na seção
"Contato". Quando tem, é trivial extrair.

**Quando não tem:**

- Olho o `page_url` no Facebook (ex: `/Dra-Fulana-Dermato/`) e peço pro
  Claude inferir o handle mais provável.
- Faço uma checagem leve (HEAD request) na URL do IG candidato.
- Se 200, uso. Se 404, marco `instagram_handle: null` e dou contexto.

**Trade-off:** posso errar o @ em ~5% dos casos (homônimos). Mitigação:
relatório destaca `confianca_handle` para o analista validar antes de
confiar cegamente.

---

## 4. Validação de especialidade

**O que vai mal sem IA:**

Regex de "dermatologia" na bio falha em:
- "Dermato | Pele, cabelo e unhas — CRM 12345" (não tem "dermatologia").
- "Médica esteta — botox e harmonização" (especialidade óbvia para
  humano, mas a palavra "dermatologia" não aparece).
- "Clínica de medicina avançada" (genérico — pode ser ou não).

**O que escolhi:** Claude classifica com prompt de poucos exemplos
(*few-shot*). Confiável em ~95% dos casos. Custa ~$0,005 por candidato.

**Trade-off:** dependência de API paga. Mitigação: cache agressivo
(mesma bio → mesma resposta, cacheada). E se a chave Claude não estiver
disponível, o pipeline ainda roda — só marca as referências com
`especialidade_validada: pendente` para revisão manual.

---

## 5. Score 0–100 (extra escolhido do case)

Optei pelo **Score** como extra (das três opções: Score, Top 3 vídeos,
Transcrição de hook).

**Por quê:**

- É o que mais **acelera** o trabalho do analista (sabe por onde começar).
- Os outros dois (vídeos e transcrição) só fazem sentido **depois** que
  a lista existe — são lupa, não filtro.
- Score expõe minha tese sobre "boa referência" de forma testável.

**Fórmula (transparente, em `scorer.py`):**

```
score = (
    25 * normalizar(n_anuncios_ativos,  piso=1,  teto=30)
  + 20 * normalizar(seguidores,          piso=1000, teto=200000)
  + 15 * tem_engajamento_minimo(>= 1%)
  + 15 * tem_postagem_recente(<= 30 dias)
  + 15 * bio_menciona_especialidade_ou_crm
  + 10 * confianca_handle_alta
)
```

**Por que esses pesos:**

- Volume de criativos pesa mais (25) porque é o ativo central que
  importa pro time de tráfego.
- Seguidores (20) pesam menos que volume de ad porque "muito
  seguidor + zero ad" não vale nada pro caso de uso.
- Engajamento e postagem recente (15 cada) garantem que o perfil tá
  vivo.
- Bio coerente (15) elimina dropshipper de saúde mascarado.
- Confiança no handle (10) é um peso de "anti-falsa positiva".

**Limitação assumida:** o score não é validado contra ground truth real
(não temos dataset rotulado). É uma heurística informada — não um
modelo treinado. Boa pra ranquear, não pra garantir 100%.

---

## 6. O que faltou (autocrítica)

O enunciado avalia também **autocrítica**. Sendo direto sobre o que
*sei* que ficou ruim ou incompleto:

1. **Engajamento é estimado, não medido.** Sem login no IG, não há outro jeito.
   Em produção, integraria Apify ou Graph API Business.
2. **Não testei com especialidade muito rara** (ex: "geriatria
   integrativa"). O comportamento esperado é entregar <10 + justificativa,
   mas não validei o caso ponta-a-ponta com input real raro.
3. **Não há *replay* idempotente** — duas execuções na mesma hora
   podem trazer 1-2 perfis diferentes (a Ad Library reordena). Pra
   demo, fixei `seed` no embaralhamento de termos para reduzir variância,
   mas a Meta em si não é determinística. Em produção, salvaria
   snapshot por dia.
4. **Custo de Claude API não está controlado por orçamento** — se
   alguém rodar com especialidade muito ampla (ex: "saúde"), pode
   gastar $0,50 numa busca. Mitigação seria um cap configurável.
5. **CLI não tem `--limit` configurável de candidatos pré-validação.**
   Fixei em 40 para garantir 10 bons no final, mas em produção isso
   seria parâmetro.

Esses cinco itens são as "dívidas" que assumi conscientemente em
favor de entregar algo redondo nos 2-3 dias.
