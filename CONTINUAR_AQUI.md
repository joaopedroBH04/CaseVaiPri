# Continuar daqui — guia do ponto atual à entrega

> **Você está aqui:** acabou de rodar `git pull origin claude/develop-case-implementation-oumwk`.
> Faltam **5 passos** até a entrega final. Tempo estimado: **25-30 min**
> (incluindo gravar o Loom).

---

## ⚠️ REGRA DE OURO — ativar o virtualenv ANTES de cada comando

**Toda vez que você abrir um terminal novo**, o virtualenv "esquece"
que estava ativo. Você precisa reativar com:

```cmd
.venv\Scripts\activate
```

**Como saber se está ativo?** Olhe o início do prompt:

| Prompt | Significado |
|--------|-------------|
| `PS C:\Users\costa\CaseVaiPri>` | ❌ NÃO está ativo. Vai falhar com `ModuleNotFoundError` |
| `(.venv) PS C:\Users\costa\CaseVaiPri>` | ✅ ATIVO. Pode rodar comandos |

Se você vir erro `No module named 'diskcache'` (ou qualquer outro),
**a causa é quase sempre essa**. Solução: rode `.venv\Scripts\activate`
e tente o comando de novo.

---

## Antes de começar (10 segundos)

Confirme onde você está e que o venv está ativo:

```cmd
cd C:\Users\costa\CaseVaiPri
.venv\Scripts\activate
git status
```

**Esperado:**

```
(.venv) PS C:\Users\costa\CaseVaiPri> git status
On branch claude/develop-case-implementation-oumwk
Your branch is up to date with 'origin/claude/develop-case-implementation-oumwk'.
nothing to commit, working tree clean
```

---

## Passo 1 — Apagar o `.env` antigo (5 segundos)

```cmd
del .env
```

> **Por que:** o `.env` que ficou da fase antiga tinha um placeholder
> de chave Anthropic, gerando o erro 401 que você viu. Apagando, a
> ferramenta roda no modo heurístico sem nenhum aviso amarelo.
>
> Se aparecer "Não foi possível encontrar o arquivo C:\Users\costa\CaseVaiPri\.env",
> está perfeito — significa que já estava apagado.

---

## Passo 1.5 — IMPORTANTE: Ativar dados reais (5 minutos, gratuito)

> **Por que esse passo é NOVO e crítico:** o Fin (avaliador da VaiPri)
> confirmou que a entrega precisa retornar **médicos reais**. O modo
> `--demo` é só pra demonstração — pra a avaliação real, a ferramenta
> precisa buscar na **Meta Ad Library Graph API oficial**.

Siga o tutorial completo em **[`docs/COMO_ATIVAR_DADOS_REAIS.md`](./docs/COMO_ATIVAR_DADOS_REAIS.md)**.

Resumo do que você vai fazer (~5 min):

1. Criar conta gratuita em [developers.facebook.com](https://developers.facebook.com)
2. Criar uma "App" (gratuita, sem aprovação necessária)
3. Pegar o **App ID** e **App Secret**
4. Gerar **Access Token** abrindo uma URL no navegador
5. Criar arquivo `.env` no projeto e colar o token

Depois disso, sempre que você rodar `vaipri-ref buscar @x dermatologia`
(sem `--demo`), vai buscar **anúncios reais** na Meta.

> **Se não quiser fazer agora**, dá pra entregar com `--demo` e incluir
> na mensagem da VaiPri: *"para testar com dados reais, sigam
> docs/COMO_ATIVAR_DADOS_REAIS.md (5 min)"*. Mas o ideal é você ter
> testado os 2 modos antes de entregar.

---

## Passo 2 — Validar que tudo funciona (1 minuto)

```cmd
pytest
```

**Esperado:**

```
............................................................. [100%]
100 passed in ~3s
```

> Se aparecer **"100 passed"** sem ERRORS, sua instalação está saudável.
> A versão anterior do bug do Windows (`WinError 32`) já foi corrigida.

---

## Passo 3 — Rodar os 3 casos de teste (2 minutos)

São os 3 testes que a VaiPri vai rodar pra avaliar. **Rode os 2 modos
pra mostrar que ambos funcionam:**

### 3a) Modo DEMO (fixtures, sempre funciona)

```cmd
vaipri-ref buscar @clinica.exemplo dermatologia --demo
vaipri-ref buscar @nutrologo.teste nutrologia --demo
vaipri-ref buscar @ortopedista.test ortopedia --demo
```

### 3b) Modo PRODUÇÃO (Graph API, se configurou o token no Passo 1.5)

```cmd
vaipri-ref buscar @clinica.exemplo dermatologia
vaipri-ref buscar @nutrologo.teste nutrologia
vaipri-ref buscar @ortopedista.test ortopedia
```

**O que deve aparecer no início do modo produção:**

```
>> Modo PRODUCAO com Graph API oficial (META_ACCESS_TOKEN OK).
```

Se aparecer linha amarela em vez disso (`META_ACCESS_TOKEN nao
configurado`), volte ao Passo 1.5.

**O que você deve ver em cada um:**

1. **Dermatologia:** tabela com 10 referências, top score ~77
2. **Nutrologia:** tabela com **9** referências + painel vermelho
   "**Lista incompleta**" com justificativa explicando que 3 candidatos
   foram filtrados (influencer, marca de produto, estética sem médico).
   **Isso é proposital** — o enunciado pede pra não inflar a lista.
3. **Ortopedia:** tabela com 10 referências, hospital foi filtrado

✅ **Checkpoint:** se os 3 rodaram sem nenhuma mensagem amarela ou
vermelha além da "Lista incompleta" da nutrologia, **está pronto pro
Loom.**

Os arquivos gerados sobrescreveram os `outputs/exemplos/` com timestamps
atualizados — sem problema.

---

## Passo 4 — Abrir a UI web (1 minuto)

Em **uma janela do terminal separada** (não feche o que você está usando):

```cmd
cd C:\Users\costa\CaseVaiPri
.venv\Scripts\activate
streamlit run app/streamlit_app.py
```

> ⚠️ **As 2 primeiras linhas são obrigatórias** em todo terminal novo,
> senão dá `ModuleNotFoundError: No module named 'diskcache'`. Não use
> `python -m streamlit` — use só `streamlit run` (com o venv ativo).

**O que acontece:**

1. Mostra `Local URL: http://localhost:8501`
2. Seu navegador abre automaticamente nessa URL
3. Interface aparece com sidebar esquerda dark

**Teste 1 vez antes do Loom:**

1. Na sidebar, deixe os defaults (`@clinica.exemplo`, dermatologia)
2. Confirme que **Modo DEMO está LIGADO**
3. Clique em **"Buscar referências"**
4. Em ~5s, a lista renderiza com cards estilizados

✅ **Checkpoint:** se os cards aparecem com avatares coloridos, scores
e botões "ver anúncios →", tá pronto pra gravar.

> **Deixe essa aba do navegador aberta.** Vai precisar dela no Loom.

---

## Passo 5 — Gravar o Loom (15-20 min)

### Antes de apertar Rec (3 min de preparo)

Abra **3 janelas/abas** prontas pra alternar:

| Janela | O que tem nela |
|--------|----------------|
| 🪟 Terminal | Pasta `CaseVaiPri`, virtualenv ativo, prompt limpo |
| 🌐 Aba A | Streamlit em `http://localhost:8501` (do Passo 4) |
| 🌐 Aba B | `outputs/exemplos/dermatologia__clinica-exemplo.html` aberto (clique 2x no arquivo) |
| 📝 Aba C | `docs/DEFINICAO_DE_PRODUTO.md` no editor (VSCode/Notepad++) |

### Instale o Loom

Se ainda não tem: [loom.com/download](https://loom.com/download). Extensão
de browser ou app desktop. Configure: **Screen + Câmera** (câmera num
canto de 200×200).

### Roteiro durante a gravação

Abra o roteiro completo: **`docs/ROTEIRO_LOOM.md`**. Lá tem 7 blocos
com tempos, falas prontas e comandos pra copiar. Segue ele linha a linha.

**Resumo do roteiro (4m30s alvo):**

| Tempo | Bloco | Você faz |
|-------|-------|----------|
| 0:00 | Contexto | Mostra README, explica o problema |
| 0:30 | Doc de produto | Abre DEFINICAO_DE_PRODUTO.md, mostra critérios |
| 1:00 | CLI ao vivo | Roda os 3 casos no terminal |
| 2:30 | UI web | Alterna pra Streamlit, faz 1 busca |
| 3:00 | Robustez | Roda 3 inputs estranhos (handle inválido etc.) |
| 3:30 | Trade-offs | Mostra TRADE_OFFS.md |
| 4:15 | Uso de Claude Code | Mostra USO_DE_CLAUDE_CODE.md |
| 4:45 | Encerramento | "Qualquer dúvida, eu defendo." |

### Comandos prontos pra copiar durante a gravação

```cmd
:: Bloco 3 (1m30s) — CLI nos 3 casos
vaipri-ref buscar @clinica.exemplo dermatologia --demo
vaipri-ref buscar @nutrologo.teste nutrologia --demo
vaipri-ref buscar @ortopedista.test ortopedia --demo

:: Bloco 4.5 (30s) — Robustez
vaipri-ref buscar @@ dermatologia --demo
vaipri-ref buscar @x.cliente neurocirurgia --demo
vaipri-ref buscar @cliente.zero.ads dermatologia --demo
```

### Depois de gravar

1. **Confira o vídeo inteiro 1 vez antes de enviar.** Foque em:
   - Áudio audível e sem cortes
   - Tela legível (texto não muito pequeno)
   - Total ≤ 5 minutos
2. Copie o link compartilhável (botão "Copy Link" no Loom)

✅ **Checkpoint:** link do Loom copiado e funcionando.

---

## Passo 6 — Empacotar e entregar (5 minutos)

### Tornar o repositório público

1. Vá pra `https://github.com/joaopedroBH04/casevaipri/settings`
2. Role até "Danger Zone" (vermelho, no fim da página)
3. Clique em **"Change repository visibility"** → **"Make public"**
4. Digite o nome do repo pra confirmar

### Mensagem de entrega pronta pra colar

Copie e cole o texto abaixo no email/Slack/Notion onde a VaiPri pediu,
substituindo apenas `[SEU LINK DO LOOM AQUI]`:

```
Time VaiPri,

Segue minha entrega da case de Analista de Automação.

Repositório (público): https://github.com/joaopedroBH04/casevaipri
Branch: claude/develop-case-implementation-oumwk
Loom (4m30s): [SEU LINK DO LOOM AQUI]

Como rodar em 60 segundos (sem precisar de chave de API):

  git clone https://github.com/joaopedroBH04/casevaipri.git
  cd casevaipri
  git checkout claude/develop-case-implementation-oumwk
  python3 -m venv .venv && source .venv/bin/activate  # Linux/Mac
  .\.venv\Scripts\activate                           # Windows
  pip install -r requirements.txt && pip install -e .
  vaipri-ref buscar @clinica.exemplo dermatologia --demo

Começo pelo `docs/DEFINICAO_DE_PRODUTO.md` (a tese antes do código).
Os 5 critérios de avaliação têm documento dedicado em `docs/`:

- 1. Definição de produto -> DEFINICAO_DE_PRODUTO.md
- 2. Tese de "bom médico"  -> DEFINICAO_DE_PRODUTO.md §1
- 3. Funciona             -> make demo + outputs/exemplos/
- 4. Uso de Claude Code   -> USO_DE_CLAUDE_CODE.md
- 5. Robustez             -> ROBUSTEZ.md (53 testes específicos)

Saídas dos 3 testes pré-geradas em outputs/exemplos/.
100 testes pytest, todos verdes.

Observação: a ferramenta tem dois modos.
- `--demo` (default na demonstração): roda com fixtures sintéticas,
  não precisa de internet aberta pra Meta nem chave de API. Pipeline
  e lógica reais — apenas a fonte de candidatos é local.
- Sem `--demo`: scraping real da Meta Ad Library. Opcionalmente usa
  ANTHROPIC_API_KEY para melhorar match de especialidade. Trade-offs
  detalhados em `docs/TRADE_OFFS.md`.

Qualquer dúvida sobre qualquer decisão, eu defendo.

Abraço,
João Pedro
```

✅ **Checkpoint final:** mensagem enviada + Loom + repo público.

---

## Verificação final de 30 segundos antes de mandar

Cole no terminal e leia a saída:

```cmd
echo === branch === & git branch --show-current
echo === sync ===   & git status --short
echo === testes === & pytest -q
echo === outputs === & dir outputs\exemplos
echo === docs ===    & dir docs
```

**Esperado:**

- Branch: `claude/develop-case-implementation-oumwk`
- Sync: (vazio)
- Testes: `100 passed`
- Outputs: 9 arquivos (3 inputs × 3 formatos)
- Docs: 6 arquivos `.md`

Se os 5 estiverem OK, **manda.**

---

## Se algo der errado durante o Loom

**Caso 0 (mais comum): "ModuleNotFoundError: No module named X"**
O virtualenv não está ativo neste terminal. Solução:
```cmd
.venv\Scripts\activate
```
e rode o comando de novo. Confirma com `(.venv)` no início do prompt.

**Caso 1: "tela ficou tremida quando alternei pra outra janela"**
Pause 2 segundos antes de alternar. O Loom corta silêncios bem depois.

**Caso 2: "errei uma frase importante"**
Não pare a gravação. Espere 2 segundos, recomece a frase do início. No
editor do Loom depois, você arrasta o cursor pro corte.

**Caso 3: "passei dos 5 minutos"**
Acelere o áudio em 1.15× no editor do Loom. Não dói.

**Caso 4: "ficou muito longo, qual bloco posso cortar?"**
Em ordem de prioridade pra cortar:
1. Bloco 6 (Uso de Claude Code) — está documentado, pode pular
2. Bloco 5 (Trade-offs) — está em doc dedicado
3. **Não corte:** Bloco 3 (CLI ao vivo) — é o coração da demo

---

## Cronograma final

```
00:00 → 00:01   Apaga .env, ativa virtualenv
00:01 → 00:02   pytest (sanity check)
00:02 → 00:03   3 buscas CLI
00:03 → 00:04   Abre Streamlit
00:04 → 00:07   Prepara janelas pro Loom
00:07 → 00:27   Grava Loom (20 min de gravação + retomadas)
00:27 → 00:32   Tornar repo público + colar mensagem + enviar
```

**Total: ~30 minutos.**

---

## Estado verificado nesta varredura (referência)

| Item | Status |
|------|--------|
| Compilação Python (23 arquivos) | ✅ |
| Imports do pacote | ✅ |
| Pytest | ✅ 100/100 |
| CLI funciona (`versao`, `--help`, `buscar`) | ✅ |
| Pipeline nos 3 casos do enunciado | ✅ (10, 9 com justificativa, 10) |
| Robustez nos 3 casos estranhos | ✅ |
| Outputs conformes ao contrato | ✅ 3/3 |
| Streamlit boot HTTP 200 | ✅ |
| Documentos | ✅ 9/9 |
| Git limpo + sincronizado | ✅ |

**Pronto. Vai.**
