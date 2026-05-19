# Roteiro do Loom — Demo da Ferramenta (alvo: 5 minutos)

> O enunciado pede **"Loom de até 5 minutos mostrando a ferramenta rodando ao vivo"**.
> Este roteiro foi desenhado para uma gravação fluida em **4m30s**, deixando
> margem pra introduções/encerramentos. Cada bloco tem o tempo-alvo,
> o que dizer e o que mostrar na tela.

---

## Antes de gravar

1. Janela do terminal aberta no projeto.
2. `.env` configurado com `ANTHROPIC_API_KEY` (se for demo "produção").
3. Streamlit pré-bootado em outra aba (`make ui` rodando em segundo plano).
4. HTML de exemplo `outputs/exemplos/dermatologia__clinica-exemplo.html`
   já aberto no navegador (uma aba de backup).
5. Resolução da tela em ≥ 1366×768 para o terminal e o browser ficarem legíveis.
6. Áudio testado. Tom de voz: explicativo e direto.

---

## Bloco 1 — Contexto (0:00 → 0:30)

**Fale:**

> "Oi, Joao Pedro aqui. Eu construi a ferramenta da case da VaiPri: um
> buscador de referencias de trafego pago para clinicas medicas.
> A ideia e simples: hoje o time da VaiPri gasta umas 4 a 6 horas
> por cliente novo procurando no Ad Library e no Instagram. Em 3
> minutos, eu entrego 10 referencias filtradas, ranqueadas e com link
> direto pros criativos."

**Mostre:**

- `README.md` aberto, especificamente a seção do diagrama do pipeline.
- Em 5 segundos, role até o título "Como o pipeline funciona".

---

## Bloco 2 — Documento de definição de produto (0:30 → 1:00)

**Fale:**

> "Antes de qualquer codigo, eu escrevi a definicao de produto.
> Defini o que e uma boa referencia em tres condicoes obrigatorias —
> anuncio ativo agora, mesma especialidade, perfil publico — e em cinco
> sinais de qualidade, que viram um score de 0 a 100. A estrategia de
> busca comeca pela Biblioteca de Anuncios da Meta, nao pelo Instagram,
> porque a Meta ja filtra de graca quem esta anunciando agora."

**Mostre:**

- Abrir `docs/DEFINICAO_DE_PRODUTO.md`.
- Destacar visualmente as 3 condições obrigatórias e os 5 sinais de qualidade.
- Rolar até a estratégia em 5 passos.

---

## Bloco 3 — Execução CLI ao vivo (1:00 → 2:30)

**Fale:**

> "Vou rodar agora ao vivo, com tres especialidades diferentes. Estou
> em modo demo pra garantir que funciona mesmo se a rede de voces
> bloquear a Meta — mas a logica de matching, score e ordenacao
> e exatamente a mesma do modo produtivo."

**No terminal, execute:**

```bash
vaipri-ref buscar @clinica.exemplo dermatologia --demo
```

> "Saida no terminal, com tabela ranqueada por score. Olhem o top 1:
> @draanalima.derm, 22 anuncios ativos, 187 mil seguidores, score 77."

**Sem pausa, execute o segundo:**

```bash
vaipri-ref buscar @nutrologo.teste nutrologia --demo
```

> "Aqui acontece algo importante: deu nove referencias, nao dez.
> Por que? Porque tres candidatos foram filtrados — um era influencer
> sem CRM, outro uma loja de suplementos, outro um studio de estetica
> sem medico. O enunciado pediu explicitamente: nao completar a lista
> com perfil ruim so pra chegar em dez. Olhem a justificativa em
> destaque no terminal."

**Execute o terceiro:**

```bash
vaipri-ref buscar @ortopedista.test ortopedia --demo
```

> "Ortopedia, dez referencias. Repare que o hospital com 28 anuncios
> ativos foi filtrado pela heuristica anti-institucional — criativo
> de hospital nao serve pra referencia de campanha individual."

---

## Bloco 4 — UI web e HTML (2:30 → 3:30)

**Fale:**

> "Mesma logica, interface visual. Util pra mostrar pro time de
> tracao sem ele precisar abrir terminal."

**Mostre:**

- Alternar pra aba do Streamlit em `http://localhost:8501`.
- Selecionar "dermatologia" + "@clinica.exemplo", clicar em "Buscar
  referencias".
- Em ~5 segundos, mostrar a lista renderizada com avatars, scores
  e botões "ver anuncios".
- Clicar em "Score breakdown" de uma referência pra mostrar a fórmula.
- Clicar em "Baixar CSV (planilha)" — abrir o CSV brevemente.

**Fale enquanto faz isso:**

> "Cada card tem o handle, link direto pra Ad Library, metricas e o
> score quebrado por parcela — volume de anuncios, seguidores,
> engajamento, postagem recente, bio coerente e confianca do handle.
> Posso baixar JSON, Markdown ou CSV pra colar em planilha."

---

## Bloco 5 — Trade-offs e autocrítica (3:30 → 4:15)

**Fale:**

> "Tres coisas que eu quero ser honesto sobre — porque o case avalia
> autocritica:"
>
> "Um: o Instagram bloqueia scraping anonimo desde 2022. Eu pego o que
> da pra pegar via Open Graph meta tags — seguidores, total de posts.
> O engajamento medio e ESTIMADO por faixa de seguidores, nao medido
> post-a-post. Pra producao real, eu integraria o Graph API Business
> ou Apify."
>
> "Dois: o score nao foi validado contra ground truth. E uma
> heuristica informada, nao um modelo treinado. Boa pra ranquear,
> nao pra garantir 100%."
>
> "Tres: rodar muitas buscas seguidas pode disparar captcha na Meta.
> Tenho cache em disco e backoff, mas a longo prazo precisaria de
> proxies rotativos ou um servico pago."

**Mostre:**

- Abrir `docs/TRADE_OFFS.md`, rolar pela tabela TL;DR no topo.

---

## Bloco 6 — Uso de Claude na construção (4:15 → 4:45)

**Fale:**

> "Por ultimo: como usei Claude no projeto. Tres jeitos, todos
> estrategicos:"
>
> "Um, o Claude API e parte do produto: gera os termos de busca da
> Ad Library, classifica especialidade, e infere handle do Instagram
> quando a pagina Facebook nao tem link."
>
> "Dois, durante o desenvolvimento: usei Claude Code pra desenhar a
> arquitetura, refatorar o parser quando dois advertisers vazavam
> dados, e escrever os 71 testes."
>
> "Tres, eu tomei todas as decisoes de produto e tese — quais filtros
> obrigatorios, qual a formula do score, onde aceitar trade-off. O
> Claude implementou; o raciocinio e meu."

---

## Bloco 7 — Encerramento (4:45 → 5:00)

**Fale:**

> "E isso. Codigo todo no repo, 71 testes verdes, 3 saidas de exemplo
> em outputs/exemplos/, e documentacao em docs/. Qualquer duvida sobre
> qualquer decisao, eu defendo. Obrigado."

---

## Dicas de gravação

- **Loom**: configure pra "screen + cam" com a câmera num canto pequeno.
- **Velocidade**: fale 10–15% mais devagar que conversa normal.
  Avaliadores vão pausar pra ler textos na tela.
- **Mouse**: use o destacador de mouse do Loom (configurações).
- **Re-gravação**: se errar uma frase, espere 2 segundos e refaça —
  o Loom tem corte rápido depois.
- **Antes de enviar**: corte os silêncios > 1.5s.

---

## Comandos prontos pra copy/paste durante a gravação

```bash
# Antes da gravação, abra:
code .                                    # editor com README/docs/
streamlit run app/streamlit_app.py &      # UI web em http://localhost:8501

# Durante a gravação, execute em sequência:
vaipri-ref buscar @clinica.exemplo dermatologia --demo
vaipri-ref buscar @nutrologo.teste  nutrologia    --demo
vaipri-ref buscar @ortopedista.test ortopedia     --demo

# Para abrir o HTML do primeiro caso (caso queira mostrar):
xdg-open outputs/exemplos/dermatologia__clinica-exemplo.html   # linux
open    outputs/exemplos/dermatologia__clinica-exemplo.html   # mac
```
