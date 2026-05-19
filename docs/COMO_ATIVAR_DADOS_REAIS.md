# Como ativar busca de dados REAIS

> O Fin confirmou: a VaiPri quer testar com **médicos reais** que
> anunciam de verdade. Este guia te leva do zero ao token funcionando
> em **~5 minutos**, **gratuito**.

---

## Por que essa configuração

A Meta protege a Biblioteca de Anúncios contra scraping anônimo. O
caminho oficial e estável pra acessar é a **Graph API Ad Library**,
que é gratuita mas exige um **access token** de um app do Facebook
Developer.

Com o token configurado, a ferramenta busca diretamente na API oficial
e retorna anúncios reais de médicos reais — funciona em qualquer rede,
sem captcha, sem 403.

---

## Passo a passo (5 min)

### 1) Cadastre-se como desenvolvedor Facebook (1 min)

Vá em **[developers.facebook.com](https://developers.facebook.com)**
e clique em **"Get Started"** (canto superior direito). Login com
sua conta Facebook pessoal. Aceita os termos.

> **Não tem conta Facebook?** Crie uma. Não precisa preencher perfil
> nem nada — apenas serve como autenticação do Developer.

### 2) Crie uma App (2 min)

**A interface da Meta muda às vezes.** O caminho mais confiável:

**Caminho rápido:** cole na barra do navegador:
```
https://developers.facebook.com/apps
```

Se você está logado, cai direto no dashboard das suas apps (vazio).
Se não estiver logado, vai pedir login antes.

**Caminhos alternativos** (se o de cima não funcionar):

- Em developers.facebook.com, canto superior direito: **"Começar"**
- Após logar, clique na sua **foto de perfil** (canto superior direito)
  → **"My Apps"** / **"Meus Apps"**

**Já no dashboard, clique em "+ Create App"** (botão verde) e siga:

1. **Use case / Caso de uso**: role a página até o final e selecione
   **"Crie um app sem um caso de uso"** (último item da lista, ícone
   de lápis preto).
   > **Por quê:** a Ad Library API é pública e não exige nenhum caso
   > de uso específico. Todos os outros (Marketing API, Login do Facebook,
   > etc.) adicionam permissões que você não precisa. Não confunda com
   > "Outro" — esse tem aviso "This option is going away soon".
2. Clique **"Próximo"** / **"Next"**.
3. **App Type / Tipo de app**: **"Business"** → **"Next"**.
4. **Nome do app**: qualquer coisa, ex: `vaipri-ref`.
5. **Email de contato**: o seu.
6. **Business account**: pode deixar em branco / "I don't want to
   connect a Business Account".
7. Clique **"Criar app"** (pode pedir senha do Facebook de novo).

> **Se pedir verificação:** Meta às vezes pede confirmar email,
> adicionar telefone, ou ativar 2FA. Faz tudo isso — leva 2-3 min
> e libera a criação.

### 3) Pegue o App ID e o App Secret (1 min)

Você cai no painel da app. No menu esquerdo:

- **"App settings"** → **"Basic"**
- Anote o **App ID** (número longo no topo)
- Clique em **"Show"** ao lado do **App Secret** → copia o valor

### 4) Gere o Access Token de App (30 segundos)

Abra esta URL no navegador, substituindo `APP_ID` e `APP_SECRET` pelos
valores que você acabou de copiar:

```
https://graph.facebook.com/oauth/access_token?client_id=APP_ID&client_secret=APP_SECRET&grant_type=client_credentials
```

A resposta vai ser um JSON tipo:

```json
{"access_token":"123456789|abcdef...","token_type":"bearer"}
```

**Copie o valor de `access_token`** inteiro (incluindo o `|` no meio).
Esse é o seu **token de App**, vale para sempre, não expira.

### 5) Cole o token no `.env` (30 segundos)

Na pasta do projeto, crie/edite o arquivo `.env`:

> ⚠️ **Atenção Windows:** o token contém o caractere `|`, que o CMD
> interpreta como pipe de comando. Não use `echo TOKEN > .env`
> diretamente — vai dar erro `'XYZ' não é reconhecido como um
> comando`. Use uma das opções abaixo:

**Opção A — Notepad (mais simples, funciona em qualquer sistema):**

```cmd
notepad .env
```

No editor que abrir, cole **uma linha** com seu token completo:

```
META_ACCESS_TOKEN=COLE-AQUI-O-TOKEN-INTEIRO-COM-O-PIPE
```

Salve com Ctrl+S e feche.

**Opção B — Windows CMD escapando o `|`:**

```cmd
echo META_ACCESS_TOKEN=123456789^|abcdef... > .env
```

O `^` antes do `|` escapa o pipe. Substitua pelos seus valores reais.

**Opção C — PowerShell (aspas simples tratam tudo como literal):**

```powershell
Set-Content -Path .env -Value 'META_ACCESS_TOKEN=COLE-AQUI-TOKEN-COMPLETO'
```

**Opção D — macOS / Linux:**

```bash
echo "META_ACCESS_TOKEN=COLE-AQUI-O-TOKEN" > .env
```

### 5.1) Confirma que ficou certo

```cmd
type .env       :: Windows
cat .env        # macOS/Linux
```

Deve aparecer uma única linha começando com `META_ACCESS_TOKEN=` e
tendo o `|` preservado no meio do valor.

### 6) Teste

```cmd
.venv\Scripts\activate
vaipri-ref buscar @clinica.exemplo dermatologia
```

> **Sem o `--demo`!** É a busca real agora.

**O que você deve ver:**

1. Linha verde: `>> Modo PRODUCAO com Graph API oficial (META_ACCESS_TOKEN OK).`
2. Progresso "consultando Meta Ad Library"
3. Tabela com referências de **médicos reais** que anunciam agora

✅ **Checkpoint:** se aparecer a tabela com nomes plausíveis (Dr./Dra.
fulano de tal, clinicas, etc.) e scores, está funcionando.

---

## Quanto custa

**Zero.** Tudo gratuito:

- Conta Facebook: gratuita
- Facebook Developer: gratuita
- App: gratuita
- Access Token de App: gratuito, não expira
- Chamadas à Ad Library API: gratuitas (rate limit ~200 chamadas/hora,
  suficiente para a demo da case)

---

## Se algo der errado

### "O App não me deixa criar / pede verificação"

Pode acontecer pra contas Facebook muito novas. Soluções:

1. Adicionar telefone à conta Facebook
2. Confirmar email
3. Esperar 24h e tentar de novo

Se nada disso funcionar, **use modo `--demo`** — a entrega da case
ainda vai cumprir o requisito principal (pipeline funciona ponta-a-ponta).

### "Token retorna 'Invalid OAuth access token'"

- Confira que copiou o token **inteiro** (com o `|`)
- Verifique se App ID e App Secret estão certos
- Tente regenerar o token via mesma URL do passo 4

### "Busca real retorna 0 resultados"

Não é bug do código — é a Meta:

1. Especialidade muito específica? Tente termos mais amplos
2. País errado no `.env`? Confira `VAIPRI_COUNTRY=BR`
3. Categoria restrita? Algumas categorias da Meta têm filtros próprios.

**Solução prática:** rode com `--demo` no Loom (sem riscos) e mencione
no vídeo que a busca real funciona com token configurado.

### "Quero usar a busca real mas não quero pedir o token pra VaiPri"

Inclua na sua mensagem de entrega:

```
Para testar com DADOS REAIS, criem um token em 5 min seguindo
docs/COMO_ATIVAR_DADOS_REAIS.md, ou usem `--demo` para validar
o pipeline.
```

Isso transfere a responsabilidade do token pra eles, mantendo a
ferramenta funcional em ambos os modos.

---

## Comparativo: modos de execução

| Modo | Comando | Dados | Quando usar |
|------|---------|-------|-------------|
| **`--demo`** | `vaipri-ref buscar @x dermatologia --demo` | Fixtures sintéticas (perfis fictícios) | Demonstrar pipeline; rede bloqueia Meta; sem token |
| **Produção (Graph API)** | `vaipri-ref buscar @x dermatologia` (com `META_ACCESS_TOKEN`) | Médicos reais que anunciam agora | Avaliação real da VaiPri |
| **Produção (scraping)** | `vaipri-ref buscar @x dermatologia` (sem token) | Real, mas Meta bloqueia frequentemente | Não recomendado — só pra testar caminho de fallback |

---

## Referências oficiais Meta

- [Ad Library API docs](https://www.facebook.com/ads/library/api/)
- [Graph API reference for ads_archive](https://developers.facebook.com/docs/graph-api/reference/ads_archive)
- [App Access Tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens#apptokens)
