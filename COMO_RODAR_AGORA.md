# Guia para lançar a case — passo a passo

> **Objetivo**: do clone à entrega para a VaiPri em **45–60 minutos**.
> **Pré-requisito mental**: ler o `README.md` por 2 min antes de começar.

---

## ⚠️ Antes de tudo: você NÃO precisa pagar nada

**A chave da API Anthropic ($5 mínimo) é totalmente opcional**. A
ferramenta entrega 100% do que o enunciado pede sem ela. Os 3 outputs
em `outputs/exemplos/` foram gerados **sem chave**, em modo heurístico,
e os 100 testes pytest passam **sem chave**.

A chave melhora qualidade em apenas 2 pontos pequenos quando você roda
em **modo produção real** (sem `--demo`), e o que vai ser apresentado
no Loom é o **modo `--demo`** — que não usa a chave de jeito nenhum.

**Recomendação direta: pule a Fase 3.** Se mais tarde a VaiPri pedir
modo produção real, você compra a chave naquele momento.

---

## Cronograma (referência)

| Fase | O que acontece                                | Tempo  |
| ---: | --------------------------------------------- | ------ |
|   0  | Pré-requisitos do laptop                      | 2 min  |
|   1  | Baixar o repositório                          | 1 min  |
|   2  | Configurar ambiente Python                    | 4 min  |
|   3  | ~~Chave Claude~~ (pule — não precisa)         | 0 min  |
|   4  | Validar instalação (rodar testes)             | 1 min  |
|   5  | Rodar os 3 casos de teste                     | 1 min  |
|   6  | Abrir a UI web (Streamlit)                    | 1 min  |
|   7  | Gravar o Loom seguindo o roteiro              | 20 min |
|   8  | Empacotar e entregar                          | 5 min  |

**Total realista: 30-35 min** (sem o Loom). Com Loom: 50-55 min.

---

## Fase 0 — Pré-requisitos do laptop (2 min)

Abra um terminal e cole **um por um** os comandos abaixo. Se algum falhar,
vá na seção "Plano B" no fim deste arquivo antes de continuar.


```bash
# 1. Python 3.10 ou superior
python3 --version
# esperado: Python 3.10.x ou Python 3.11.x ou Python 3.12.x
# se aparecer 3.9 ou inferior, instale: https://www.python.org/downloads/

# 2. pip funcionando
python3 -m pip --version

# 3. Git instalado
git --version

# 4. Make (opcional, mas facilita)
make --version || echo "make nao instalado — tudo bem, usaremos comandos diretos"
```

✅ **Checkpoint:** os 3 primeiros comandos retornaram versão válida.

---

## Fase 1 — Baixar o repositório (1 min)

Você já fez commit + push para o branch `claude/develop-case-implementation-oumwk`.
Agora, no **seu laptop**:

```bash
# 1. Clona o repositorio
git clone https://github.com/joaopedroBH04/CaseVaiPri.git
cd CaseVaiPri

# 2. Pega a branch com a implementacao
git checkout claude/develop-case-implementation-oumwk

# 3. Verifica a estrutura
ls
```

**Você deve ver:**

```
COMO_RODAR_AGORA.md  Makefile             README.md            app/
docs/                outputs/             pyproject.toml       requirements.txt
scripts/             src/                 tests/
```

✅ **Checkpoint:** se ver os 12 itens acima, está no lugar certo.

---

## Fase 2 — Configurar ambiente Python (4 min)

```bash
# 1. Criar virtualenv isolado (nao mistura com Python global)
python3 -m venv .venv

# 2. Ativar o virtualenv
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\activate         # Windows PowerShell

# Voce sabe que ativou quando o prompt vira: (.venv) seu-user@laptop $

# 3. Atualizar pip
pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements.txt

# Aguarde ~2 min. Esperado: ~30 pacotes instalados sem erro.

# 5. Instalar o pacote em modo editavel (faz o comando 'vaipri-ref' funcionar)
pip install -e .

# 6. (Opcional, so se for rodar scraping REAL contra a Meta)
python -m playwright install chromium
# isso baixa o Chromium (~150MB) que o Playwright usa pra scraping.
# Em modo --demo, NAO precisa disso.
```

✅ **Checkpoint:** rode `vaipri-ref versao` e veja `vaipri-ref versao 0.1.0`.

---

## Fase 3 — Chave Claude (PULE — não precisa)

> **Resumo:** essa fase existe para quem quer rodar em **modo produção
> real** (scraping ao vivo da Meta). Para entregar a case, **você NÃO
> precisa fazer nada aqui.**

### Por que pular

| Pergunta                                                                | Resposta                                                              |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| A ferramenta funciona sem chave?                                        | **Sim.** 100 testes passam sem chave.                                 |
| Os 3 outputs em `outputs/exemplos/` foram gerados sem chave?            | **Sim**, em modo heurístico.                                          |
| O Loom usa `--demo`. Demo usa a chave?                                   | **Não.** Em modo `--demo` a chave é literalmente ignorada.            |
| A chave evita a Meta me bloquear?                                       | **Não.** A chave é da Anthropic; o bloqueio é da Meta. Coisas diferentes. |
| Posso entregar a case sem pagar nada?                                   | **Sim.** Pule esta fase e siga para a Fase 4.                         |

### Se mesmo assim quiser configurar (modo produção real depois)

Faz sentido se você (a) tem rede caseira aberta, (b) quer mostrar a
ferramenta indo na Meta ao vivo, (c) tem 30min sobrando para testar
fora do escopo da case.

```bash
# 1. Copia o template
cp .env.example .env

# 2. Edita o .env e cola sua chave
nano .env       # ou: code .env, vim .env

# Linha que você vai modificar:
# ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# 3. Checa se foi detectada
python3 -c "from vaipri_ref.config import carregar; c=carregar(); print('Claude:', 'OK' if c.tem_chave_anthropic else 'NAO CONFIGURADA')"
```

✅ **Checkpoint (se pulou):** o arquivo `.env` não existe ou está
sem chave válida. **Tudo bem.** Siga para a Fase 4.

---

## Fase 4 — Validar instalação rodando testes (1 min)

```bash
pytest
```

**Esperado:**

```
............................................. [100%]
100 passed in 1.0s
```

✅ **Checkpoint:** se você vir **"100 passed"**, sua instalação está **100% saudável**.

> Se aparecer **menos de 100** ou erro, vá em "Plano B" no fim do documento.

---

## Fase 5 — Rodar os 3 casos de teste (1 min)

Esse é o teste que a VaiPri vai fazer: rodar a ferramenta com 3 inputs
diferentes e ver o que sai.

```bash
# Caso 1: dermatologia
vaipri-ref buscar @clinica.exemplo dermatologia --demo

# Caso 2: nutrologia
vaipri-ref buscar @nutrologo.teste nutrologia --demo

# Caso 3: ortopedia
vaipri-ref buscar @ortopedista.test ortopedia --demo
```

**O que você deve ver para CADA caso:**

1. Barra de progresso animada
2. Tabela ranqueada com as 10 referências (ou menos com justificativa)
3. Paths dos 3 arquivos gerados (JSON, MD, HTML)

**Para o caso `nutrologia`**, especificamente, você deve ver:

```
╭───── Lista incompleta ─────╮
│ Foram encontradas apenas 9 referencias que cumprem TODOS os criterios...
╰─────────────────────────────╯
```

Isso é **proposital**: o enunciado pede para não completar com perfis ruins.

**Onde foram salvos:**

```bash
ls outputs/exemplos/
```

Você verá 9 arquivos (3 inputs × 3 formatos):

```
dermatologia__clinica-exemplo.{json,md,html}
nutrologia__nutrologo-teste.{json,md,html}
ortopedia__ortopedista-test.{json,md,html}
```

✅ **Checkpoint:** abra um dos HTMLs no navegador:

```bash
# macOS:
open outputs/exemplos/dermatologia__clinica-exemplo.html

# Linux:
xdg-open outputs/exemplos/dermatologia__clinica-exemplo.html

# Windows:
start outputs/exemplos/dermatologia__clinica-exemplo.html
```

Deve aparecer uma página dark com os cards das 10 referências, score
0-100 destacado, e link "ver anúncios →" funcionando em cada card.

---

## Fase 6 — Abrir a UI web (1 min, recomendado para o Loom)

```bash
streamlit run app/streamlit_app.py
```

**O que acontece:**

1. Terminal mostra `Local URL: http://localhost:8501`
2. Seu navegador abre automaticamente nessa URL
3. Você vê a interface com sidebar esquerda

**Use:**

1. Na sidebar, deixe `@ do cliente` = `@clinica.exemplo`
2. `Especialidade` = `dermatologia`
3. Mantenha "Modo DEMO" ligado
4. Clique em **Buscar referências**
5. Aguarde ~5 segundos
6. Veja a lista renderizada com cards estilizados

✅ **Checkpoint:** se o card de cada referência aparece com avatar,
métricas, score e botão "ver anúncios", está perfeito para gravar o Loom.

> **Deixe esta aba aberta para a gravação.**

---

## Fase 7 — Gravar o Loom (20 min, sem pressa)

O case pede explicitamente: **"Loom de até 5 minutos mostrando a
ferramenta rodando ao vivo. Esse é importante."**

### Antes de gravar

1. Instale o Loom: [loom.com/download](https://loom.com/download) — extensão
   de browser ou app desktop. Ambos funcionam.
2. Teste o microfone (Loom faz um sound check no início).
3. Configure: **Screen + Câmera** (cam num cantinho de 200px).
4. Resolução do desktop em **1920×1080** se possível.

### Pré-cena (1 min antes de apertar Rec)

Abra estas 3 janelas, em sequência fácil de alternar:

| Janela              | O que vai estar nela                                                  |
| ------------------- | --------------------------------------------------------------------- |
| Terminal #1         | Pasta `CaseVaiPri`, virtualenv ativo, prompt limpo                    |
| Navegador aba A     | Streamlit em `http://localhost:8501` (já rodando da Fase 6)           |
| Navegador aba B     | `outputs/exemplos/dermatologia__clinica-exemplo.html` aberto          |
| Editor de texto     | `docs/DEFINICAO_DE_PRODUTO.md` aberto, rolado pro topo                |

### Durante a gravação

Abra `docs/ROTEIRO_LOOM.md` em um segundo monitor (ou imprima) e
**siga bloco a bloco**. O roteiro tem **6 blocos** com tempos:

| Bloco                                       | Tempo  |
| ------------------------------------------- | ------ |
| 1. Contexto                                 | 0:30   |
| 2. Documento de definição de produto        | 0:30   |
| 3. Execução CLI ao vivo (3 inputs)          | 1:30   |
| 4. UI web + HTML                            | 1:00   |
| 4.5. Robustez ao vivo (3 casos do enunciado)| 0:30   |
| 5. Trade-offs e autocrítica                 | 0:45   |
| 6. Uso de Claude Code                       | 0:30   |
| 7. Encerramento                             | 0:15   |
| **Total alvo**                              | ~4:30  |

> **Dica de ouro:** se errar uma frase, pause 2 segundos, recomece
> a frase do início. O Loom corta silêncios facilmente depois.

### Comandos prontos pra copiar durante a gravação (apenas estes)

```bash
# Bloco 3 — CLI ao vivo
vaipri-ref buscar @clinica.exemplo dermatologia --demo
vaipri-ref buscar @nutrologo.teste nutrologia --demo
vaipri-ref buscar @ortopedista.test ortopedia --demo

# Bloco 4.5 — Robustez (cada comando mostra um comportamento diferente)
vaipri-ref buscar @@ dermatologia --demo                        # handle invalido
vaipri-ref buscar @x.cliente neurocirurgia --demo               # especialidade rara
vaipri-ref buscar @cliente.zero.ads dermatologia --demo         # cliente sem ads
```

### Depois de gravar

1. Loom processa em background (uns 30s).
2. **Copie o link compartilhável** (botão "Copy Link" no Loom).
3. **Confira o vídeo inteiro 1 vez antes de enviar.**

✅ **Checkpoint:** vídeo com menos de 5 minutos, áudio audível, tela legível.

---

## Fase 8 — Empacotar e entregar (5 min)

A VaiPri pediu uma das duas opções: **GitHub público** ou **ZIP**.

### Opção A — GitHub público (recomendado)

```bash
# 1. Certifique-se de estar no branch certo
git status
# esperado: "On branch claude/develop-case-implementation-oumwk"

# 2. Verifique que tudo foi pushado
git log origin/claude/develop-case-implementation-oumwk..HEAD
# esperado: vazio (significa que local = remoto)

# 3. (Opcional) faça merge pra main pra a entrega
git checkout main 2>/dev/null || git checkout -b main
git merge claude/develop-case-implementation-oumwk
git push -u origin main
```

Agora **deixe o repositório público** no GitHub:

1. Vá para `https://github.com/joaopedroBH04/CaseVaiPri/settings`
2. Role até "Danger Zone"
3. Clique em **"Change repository visibility"** → **Make public**
4. Confirme

### Opção B — ZIP

```bash
# Limpa arquivos que nao precisam ir no zip
make clean

# Cria o zip excluindo .venv, .cache, .git, __pycache__
cd ..
zip -r CaseVaiPri-JoaoPedro.zip CaseVaiPri \
  -x "CaseVaiPri/.venv/*" \
  -x "CaseVaiPri/.cache/*" \
  -x "CaseVaiPri/.git/*" \
  -x "*/__pycache__/*" \
  -x "*/.pytest_cache/*" \
  -x "*/.DS_Store"

ls -lh CaseVaiPri-JoaoPedro.zip
# esperado: 1-2 MB
```

### Mensagem de entrega (cole no email/Slack/Notion da VaiPri)

```
Time VaiPri,

Segue minha entrega da case de Analista de Automação.

Repositorio (publico): https://github.com/joaopedroBH04/CaseVaiPri
Branch: claude/develop-case-implementation-oumwk
Loom (4m30s): [SEU LINK AQUI]

Como rodar em 60 segundos (sem precisar de nenhuma chave de API):

  git clone https://github.com/joaopedroBH04/CaseVaiPri.git
  cd CaseVaiPri
  git checkout claude/develop-case-implementation-oumwk
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt && pip install -e .
  vaipri-ref buscar @clinica.exemplo dermatologia --demo

Comeco pelo `docs/DEFINICAO_DE_PRODUTO.md` (a tese antes do codigo).
Os 5 criterios de avaliacao tem documento dedicado em `docs/`:

- 1. Definicao de produto -> DEFINICAO_DE_PRODUTO.md
- 2. Tese de "bom medico" -> DEFINICAO_DE_PRODUTO.md §1
- 3. Funciona            -> make demo + outputs/exemplos/
- 4. Uso de Claude Code  -> USO_DE_CLAUDE_CODE.md
- 5. Robustez            -> ROBUSTEZ.md (53 testes especificos)

Saidas dos 3 testes pre-gerados em outputs/exemplos/.
100 testes pytest, todos verdes.

Observacao: a ferramenta tem dois modos.
- `--demo` (default na demonstracao): roda com fixtures sinteticas,
  nao precisa de internet aberta para Meta nem chave de API. Pipeline
  e logica reais — apenas a fonte de candidatos e local.
- Sem `--demo`: scraping real da Meta Ad Library. Opcionalmente usa
  ANTHROPIC_API_KEY para melhorar match de especialidade. Trade-offs
  detalhados em `docs/TRADE_OFFS.md`.

Qualquer duvida, eu defendo cada decisao.

Abraço,
Joao Pedro
```

✅ **Checkpoint final:** repositório público OU zip pronto + link do Loom.

---

## Verificação final antes de mandar (1 min)

Cole isso no terminal e leia a saída — todos devem estar OK:

```bash
echo "[1] Branch correta:" && git branch --show-current
echo "[2] Tudo commitado:" && git status --short
echo "[3] Testes verdes:"   && pytest -q 2>&1 | tail -1
echo "[4] Outputs gerados:" && ls outputs/exemplos/ | wc -l
echo "[5] Docs presentes:"  && ls docs/ | wc -l
```

Esperado:

```
[1] Branch correta: claude/develop-case-implementation-oumwk
[2] Tudo commitado: (vazio)
[3] Testes verdes: 100 passed in 1.0s
[4] Outputs gerados: 9
[5] Docs presentes: 6
```

---

## Plano B (quando algo der errado)

### "Python --version mostra 3.9"

Instale Python 3.11 com pyenv:

```bash
# macOS: brew install pyenv
# Linux: curl https://pyenv.run | bash

pyenv install 3.11.9
pyenv local 3.11.9
python3 --version  # agora vai mostrar 3.11.9
```

### "pip install falha em algum pacote"

Provavelmente é o `lxml` que precisa de libs do sistema:

```bash
# Ubuntu/Debian:
sudo apt install libxml2-dev libxslt-dev

# macOS:
brew install libxml2 libxslt

# Depois tente de novo:
pip install -r requirements.txt
```

### "vaipri-ref: command not found"

O `pip install -e .` não rodou ou o virtualenv não está ativo.

```bash
# Verifique:
which python   # deve apontar pra .venv/bin/python
which vaipri-ref  # deve apontar pra .venv/bin/vaipri-ref

# Se nao, reative o virtualenv:
source .venv/bin/activate
pip install -e .
```

### "Streamlit nao abre"

Talvez a porta 8501 esteja ocupada. Use outra:

```bash
streamlit run app/streamlit_app.py --server.port 8888
# abra http://localhost:8888
```

### "Tenho rede aberta — quero rodar SEM --demo"

> Esse caminho é **opcional** e só vale o esforço se você quiser
> demonstrar o scraping real ao vivo. **Não é necessário para entregar
> a case** — o modo `--demo` cobre 100% do que o enunciado pede.

```bash
# 1. (Opcional) Configure ANTHROPIC_API_KEY no .env — melhora o match
#    de especialidade. Funciona sem também, em modo heurístico.
# 2. Instale o Chromium do Playwright
python -m playwright install chromium

# 3. Rode sem --demo
vaipri-ref buscar @clinica.exemplo dermatologia --verbose
```

Se a Meta bloquear (403/captcha), reduza para `--top 5` e use cache:

```bash
vaipri-ref buscar @clinica.exemplo dermatologia --top 5
```

### "Vou apresentar e tenho medo de a Meta cair na hora"

Use modo `--demo`. Tudo bem dizer no Loom:
*"Estou em modo demo agora; o pipeline real funciona igual, está em
`pipeline.py:80-115`, e tem trade-offs documentados em
`docs/TRADE_OFFS.md`"*.

A VaiPri valoriza honestidade técnica — é literalmente um dos 4 critérios
gerais da case.

---

### "Devo pagar a chave da Anthropic?"

**Não para entregar a case.** A chave custa no mínimo $5 e não dá
garantia de nada — o que pode dar errado em produção (bloqueio da
Meta, captcha, mudança de layout) **não tem relação com a chave**, é
risco da Meta. O modo `--demo` é determinístico e funciona sempre.

A chave só vale se você quer mostrar o scraping real funcionando ao
vivo da sua rede caseira, e topa o risco de a Meta bloquear na hora
do teste. Pra entregar a case com qualidade, não precisa.

### "Recebi erro 401 ou 'invalid x-api-key'"

Quer dizer que existe um `.env` com algo no campo `ANTHROPIC_API_KEY`,
e esse "algo" é um placeholder (provavelmente `sk-ant-xxxxxx...`) ou
chave inválida. **Solução: apague o `.env`**:

```bash
# macOS / Linux:
rm .env

# Windows:
del .env
```

A ferramenta vai detectar placeholder automaticamente agora, mas se
ainda assim quiser remover qualquer chance de confusão, apagar o
`.env` resolve. Em seguida rode `vaipri-ref buscar ... --demo` normal.

---

## Resumo cronológico

```
0:00 → 0:02   Pre-requisitos
0:02 → 0:03   Clone do repo
0:03 → 0:07   Instalar deps
0:07 → 0:07   Fase 3 PULADA (chave Claude nao e necessaria)
0:07 → 0:08   Rodar testes (100 verdes)
0:08 → 0:09   Rodar 3 casos de teste
0:09 → 0:10   Abrir Streamlit
0:10 → 0:30   Gravar Loom de 4m30s
0:30 → 0:35   Empacotar + enviar
```

**Pronto. Você acabou de entregar a case — gastando R$ 0.**
