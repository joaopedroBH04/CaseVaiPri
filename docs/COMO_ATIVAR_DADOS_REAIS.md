# Como ativar busca de DADOS REAIS

> O Fin (avaliador VaiPri) confirmou: a entrega precisa retornar
> **médicos reais** que anunciam no Meta agora, com **métricas reais**
> do Instagram (seguidores, engajamento, posts).
>
> A maneira mais confiável e gratuita: **Apify**. ~5 minutos de setup.

---

## TL;DR — caminho recomendado (Apify)

1. **Cria conta** em [apify.com/sign-up](https://apify.com/sign-up) (Google ok)
2. **Pega token** em Settings → Integrations → Personal API tokens
3. **Cola no `.env`**: `APIFY_API_TOKEN=apify_api_xxxxxxxxxxxx`
4. **Roda**: `vaipri-ref buscar @clinica.exemplo dermatologia`

Custo: **$5 grátis no primeiro cadastro** = ~10 buscas completas. Mais
que suficiente para a avaliação da VaiPri.

---

## Por que Apify resolve TUDO

A entrega precisa de 3 coisas que estão bloqueadas para scraping anônimo:

| Item do enunciado | Bloqueado por | Como Apify resolve |
|------------------|---------------|---------------------|
| Anúncios reais com nome real da página | Meta serve HTML vazio | Actor `facebook-ads-library-scraper` renderiza igual o browser |
| Handle Instagram de cada anunciante | Meta não dá no JSON inicial | Actor extrai do anúncio renderizado |
| Métricas IG (seguidores, engajamento) | IG bloqueia desde 2022 sem login | Actor `instagram-profile-scraper` pega tudo |

**Sem Apify**, a entrega só consegue lista parcial sem métricas. **Com
Apify**, atende 100% do que o enunciado pede.

---

## Passo a passo detalhado

### 1) Cria conta na Apify (2 min)

Vai em [apify.com/sign-up](https://apify.com/sign-up).

- "Sign up with Google" é o mais rápido — usa sua conta Gmail
- Pode pular tour inicial

Você cai no dashboard. **Importante**: na lateral direita, confira
"$5.00 free credit" — esse é seu crédito inicial.

### 2) Pega o API token (1 min)

No dashboard:

1. Clica na **foto de perfil** (canto superior direito)
2. **Settings** → **Integrations**
3. Aba **Personal API tokens** (geralmente já vem selecionada)
4. Você verá um token gerado automaticamente. Copia o valor inteiro
   (começa com `apify_api_`).

Se não tiver nenhum token visível:
- Clica **Create new token**
- Nome: qualquer coisa, ex: `vaipri-ref`
- Permissions: deixa default
- Copia

### 3) Cola no `.env` (30 segundos)

Na pasta do projeto, abre o `.env` (cria se não existir):

**Windows (notepad):**
```cmd
notepad .env
```

**macOS / Linux:**
```bash
nano .env   # ou code .env, vim .env
```

Adiciona a linha:

```
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Substitui pelo token real. Salva e fecha.

### 4) Testa

```cmd
vaipri-ref buscar @clinica.exemplo dermatologia
```

**O que deve aparecer no topo:**

```
>> Modo PRODUCAO com Apify (caminho recomendado — dados reais completos).
```

Aguarda ~1-2 min (Apify roda actor na infra deles). No fim, você vê
a tabela com **médicos reais** que anunciam, com:

- Handle Instagram real (não inferido)
- Seguidores reais
- Engajamento real (calculado dos últimos posts)
- Nota 0-10 com avaliação ("Excelente", "Muito boa", etc.)

✅ **Checkpoint:** se aparecer @ válido + número de seguidores
verdadeiro pra pelo menos algumas referências, **está funcionando**.

---

## Quanto vai custar na prática

Apify cobra por **uso de actor** (compute time + tráfego). Estimativas:

| Operação | Custo aprox. |
|---------|-------------|
| 1 keyword na Ad Library (50 ads) | $0.02-0.05 |
| 1 perfil Instagram com posts | $0.02-0.05 |
| 1 busca completa (10 keywords + 10 perfis) | **$0.40-0.70** |
| $5 grátis ÷ $0.50 médio | **~10 buscas completas** |

Mais que suficiente pra:
- Você testar (3-4 buscas)
- A VaiPri testar com 3 inputs (3 buscas)
- Sobra reserva

**Se acabar o crédito grátis**, é só:
- Pause/cancele os actors (não cobra recorrente)
- Ou adicione método de pagamento (cobrança por uso)

---

## Custo Apify vs Anthropic

Você não precisa dos **dois**. Comparativo:

| Caminho | Custo | Resolve |
|---------|-------|---------|
| Só Apify | **$0** (grátis no cadastro) | ✅ Dados reais + métricas (100% do enunciado) |
| Só Anthropic | $5 (mínimo de pagamento) | ❌ Match melhor mas SEM dados reais |
| Os dois | $5 | ✅ Tudo + qualidade máxima |

**Recomendação:** Apify primeiro (grátis, resolve o essencial). Se
sobrar tempo/grana, Anthropic depois.

---

## Se algo der errado

### "Token Apify inválido"

- Confirma que copiou inteiro (começa com `apify_api_`, ~40 chars)
- Verifica que está no `.env` na pasta correta
- Rode `type .env` (Windows) ou `cat .env` (mac/linux)

### "Apify retornou 402 Payment Required"

Acabou o crédito grátis. Opções:
- Esperar próximo mês (renova mensal? — depende)
- Adicionar cartão pra pagar por uso
- Voltar pro modo `--demo` (sempre funciona)

### "Apify deu timeout"

Actors complexos podem demorar. Mitigações:
- O `_run_sync` tem timeout de 180s
- Tente em horário de menos uso (off-peak)
- Verifique o painel da Apify para ver runs travados

### "Actor não encontrado"

A Apify às vezes muda nome ou remove actors. Pode trocar via env:

```
APIFY_AD_LIBRARY_ACTOR=outro/actor-name
APIFY_IG_ACTOR=outro/ig-scraper
```

Verifique [apify.com/store](https://apify.com/store) os actors disponíveis.

---

## Comparativo: modos de execução

| Modo | Comando | Dados | Quando usar |
|------|---------|-------|-------------|
| **Apify (recomendado)** | `vaipri-ref buscar @x dermatologia` (com `APIFY_API_TOKEN`) | **Dados REAIS de médicos reais com métricas** | Avaliação da VaiPri |
| `--demo` | `vaipri-ref buscar @x dermatologia --demo` | Fixtures sintéticas | Sem chave, sem rede |
| Meta Graph API | (com `META_ACCESS_TOKEN` sem App Review) | Apenas page IDs | Não recomendado (rejeitado pela Meta) |
| Scraping HTTP | (sem nenhum token) | Page IDs sem nomes | Último fallback |

---

## Referências

- [Apify Platform](https://apify.com)
- [Apify Store — Actors](https://apify.com/store)
- [API REST docs](https://docs.apify.com/api/v2)
- [Actor Facebook Ads Library Scraper](https://apify.com/curious_coder/facebook-ads-library-scraper)
- [Actor Instagram Profile Scraper](https://apify.com/apify/instagram-profile-scraper)
