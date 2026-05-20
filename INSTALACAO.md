# Instalação — do zero ao funcionando

> Guia definitivo. Se você seguir cada passo na ordem, em **~10 minutos**
> a ferramenta vai estar rodando com dados reais. Sem nada mais.

---

## Pré-requisitos do laptop

Antes de começar, confirme no terminal:

```bash
python3 --version     # precisa ser 3.10 ou superior
pip3 --version
git --version
```

**Se alguma falhar:**

- **Python**: baixe em [python.org/downloads](https://www.python.org/downloads/) (≥ 3.10)
- **Git**: baixe em [git-scm.com](https://git-scm.com/downloads)
- **Windows**: durante a instalação do Python, marque "Add Python to PATH"

---

## Passo 1 — Clonar o repositório (1 min)

```bash
git clone https://github.com/joaopedroBH04/CaseVaiPri.git
cd CaseVaiPri
git checkout claude/develop-case-implementation-oumwk
```

Confirme:

```bash
ls
# deve listar: app/  docs/  outputs/  scripts/  src/  tests/  README.md  ...
```

---

## Passo 2 — Criar ambiente virtual (2 min)

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
```

**Confirme que o virtualenv ativou:** o prompt do terminal deve mostrar
`(.venv)` no início. Exemplo:

```
(.venv) PS C:\Users\costa\CaseVaiPri>
```

> ⚠️ **Importante:** todo terminal novo que você abrir vai precisar
> rodar `.venv\Scripts\activate` (ou `source .venv/bin/activate`).
> Sem isso, comando `vaipri-ref` não funciona.

---

## Passo 3 — Instalar dependências (3 min)

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

**Confirme que instalou:**

```bash
vaipri-ref versao
# deve mostrar: vaipri-ref versao 0.1.0
```

---

## Passo 4 — Configurar o `.env` (3 min — passo CRÍTICO)

A ferramenta tem 3 chaves de API. Apenas **uma é obrigatória** pra
ter dados reais:

| Chave              | Obrigatória? | Custo            | Para que serve                          |
| ------------------ | :----------: | ---------------- | --------------------------------------- |
| `APIFY_API_TOKEN`  | **SIM** ✅   | **$0** ($5 grátis) | Dados reais (Ad Library + Instagram)    |
| `META_ACCESS_TOKEN`| Opcional     | $0               | Caminho alternativo (limitado pela Meta)|
| `ANTHROPIC_API_KEY`| Opcional     | $5+              | Melhora match (mas não é necessária)    |

### 4.1 — Pegar o token Apify (essencial)

1. Acesse [**apify.com/sign-up**](https://apify.com/sign-up) e crie conta (login com Google é mais rápido)
2. No dashboard, clique na **foto de perfil** (canto superior direito)
3. **Settings** → **Integrations** → **Personal API tokens**
4. Copie o token (formato `apify_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

> Você ganha **$5 grátis** de crédito ao criar a conta = ~10 buscas
> completas. Suficiente pra avaliação.

### 4.2 — Criar o arquivo `.env`

Na pasta `CaseVaiPri`, crie um arquivo chamado `.env` com este conteúdo:

```
APIFY_API_TOKEN=cole_aqui_o_seu_token_apify
```

> ⚠️ **Windows + token com `|`**: o CMD interpreta `|` como pipe. Se
> seu token tiver `|` (raro em Apify, comum em Meta), use o Notepad
> em vez de `echo`:
>
> ```cmd
> notepad .env
> ```

### 4.3 — Validar a configuração

```bash
vaipri-ref check
```

**Esperado** (algo como):

```
✓ APIFY_API_TOKEN: Token aceito pela Apify (conta: seu_username).
— META_ACCESS_TOKEN: nao configurado (opcional, Apify e' o caminho principal).
— ANTHROPIC_API_KEY: nao configurada (opcional).

País: BR
Top N: 10
Max candidatos: 40
```

✅ **Se vir `✓ APIFY_API_TOKEN`, está pronto.**

❌ Se vir vermelho/amarelo: confira que copiou o token inteiro (sem espaços)
e está no mesmo diretório do projeto.

---

## Passo 5 — Validar que funciona (2 min)

### 5.1 — Rodar a suite de testes

```bash
pytest
```

**Esperado**: `116 passed in ~8s`. Se vir falhas, ative o virtualenv
de novo e reinstale (`pip install -e .`).

### 5.2 — Primeira busca (modo demo, instantâneo)

```bash
vaipri-ref buscar "@clinica.exemplo" dermatologia --demo
```

> No Windows PowerShell, **sempre coloque o `@cliente` entre aspas**, senão o
> PowerShell interpreta `@` como operador especial e dá erro.

Deve aparecer uma tabela com 10 médicos fictícios. Isso valida o pipeline.

### 5.3 — Busca REAL com dados de verdade

```bash
vaipri-ref buscar "@clinica.exemplo" dermatologia
```

Sem `--demo`. Vai usar Apify, leva 1–2 minutos. Deve aparecer:

- `>> Modo PRODUCAO com Apify (caminho recomendado — dados reais completos).`
- Tabela com **médicos reais** (handles `@dr.alguem`)
- Seguidores reais, engajamento real, número correto de anúncios

---

## Passo 6 — Abrir a interface web (opcional, mas recomendado)

```bash
streamlit run app/streamlit_app.py
```

Vai abrir `http://localhost:8501` no navegador. Preenche o formulário
e clica em "Buscar referências".

---

## Estrutura de tokens recomendada (resumo)

```
.env  (cole na raiz do projeto)
├── APIFY_API_TOKEN=apify_api_xxxxxxxxxxxx       ← ESSENCIAL
├── META_ACCESS_TOKEN=...                         ← opcional, não use sem necessidade
└── ANTHROPIC_API_KEY=sk-ant-...                  ← opcional, não use sem necessidade
```

Você pode **comentar com `#`** ou **apagar a linha** das que não usar.

---

## Comandos úteis

| Comando | O que faz |
|---------|-----------|
| `vaipri-ref check` | Diagnóstico das chaves configuradas |
| `vaipri-ref buscar "@x" dermatologia` | Busca real (Apify) |
| `vaipri-ref buscar "@x" dermatologia --demo` | Busca em modo demo (fixtures sintéticas) |
| `vaipri-ref limpar-cache` | Apaga cache para forçar busca fresca |
| `vaipri-ref versao` | Mostra a versão instalada |
| `streamlit run app/streamlit_app.py` | Sobe a interface web |
| `pytest` | Roda os 116 testes automatizados |

---

## Resolução de problemas comuns

### `vaipri-ref: comando não reconhecido`

O virtualenv não está ativo. Rode:

```bash
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # macOS/Linux
```

### `'@clinica' não pode ser usado em expressão` (PowerShell)

Use aspas: `vaipri-ref buscar "@clinica.exemplo" dermatologia`

### `ModuleNotFoundError: No module named 'X'`

Reinstale:
```bash
pip install -r requirements.txt
pip install -e .
```

### Apify retorna 0 resultados

```bash
vaipri-ref limpar-cache
vaipri-ref check        # confirma que o token está OK
vaipri-ref buscar "@cliente.exemplo" dermatologia
```

Se ainda assim vier vazio, o crédito grátis pode ter acabado. Veja
em `apify.com` → Billing.

### Erro com `|` no token (Windows)

Use o **Notepad** em vez do `echo`:
```cmd
notepad .env
```

---

## O que NÃO precisa instalar

- Não precisa de Docker
- Não precisa de Node.js / Java / Ruby
- Não precisa de PostgreSQL/MySQL — usamos cache local em arquivo
- Não precisa de chave Anthropic ($5) — a ferramenta funciona sem
- Não precisa criar conta no Meta Developer — Apify resolve

**Só Python + Git + token Apify ($0).**
