# Robustez (resposta direta ao criterio 5)

> O enunciado avalia explicitamente: *"Robustez — o que acontece quando
> o input e estranho? @ que nao existe, especialidade rara, perfil sem
> nenhum anuncio?"*

Cada um dos 3 casos esta coberto por testes automatizados em
[`tests/test_robustez.py`](../tests/test_robustez.py) (29 testes, todos verdes).

---

## Caso A: "@ que nao existe"

Dois subcasos: handle **sintaticamente invalido** e handle **valido mas
inexistente** no Instagram.

### A.1 — Handle sintaticamente invalido

**Entradas testadas:** `""`, `"@@"`, `"user@host"`, `"a b c"`, `"x" * 31`,
`"  "` (so espacos).

**Comportamento:** `ValueError` levantado **antes** de qualquer chamada
externa, com mensagem clara contendo a palavra "handle" ou "invalido".

**Teste:** `tests/test_robustez.py::TestHandleNaoExiste::test_handle_sintaticamente_invalido_rejeitado_cedo`.

**Onde no codigo:** `src/vaipri_ref/utils/normalize.py::limpar_handle`
(linhas 19-39). Tambem chamado em `pipeline.py:55`.

```bash
$ vaipri-ref buscar @@ dermatologia --demo
erro fatal: Handle do cliente invalido: handle invalido: '@@'
```

### A.2 — Handle sintaticamente valido mas inexistente

**Entrada:** `@clinica.que.nao.existe.99999`.

**Comportamento:** ferramenta **continua** normalmente. O @ do cliente
serve apenas para **excluir o cliente da lista de referencias** (se por
acaso ele aparecer entre os candidatos). Como o cliente nao existe,
nada e excluido, e as referencias sao retornadas normalmente.

**Teste:** `tests/test_robustez.py::TestHandleNaoExiste::test_handle_inexistente_no_ig_nao_quebra_busca`.

### A.3 — Robustez extra: aceita URL completa em vez de @

**Entrada:** `https://www.instagram.com/dra.fulana/`.

**Comportamento:** URL e normalizada para `dra.fulana`. Avaliador pode
colar do navegador sem se preocupar.

**Teste:** `tests/test_robustez.py::TestHandleNaoExiste::test_limpar_handle_aceita_urls_completas`.

---

## Caso B: "Especialidade rara"

Cobre 4 subcasos relevantes pro avaliador.

### B.1 — Especialidade sem fixture (modo demo)

**Entrada:** `--demo neuro-pediatria` (fora das 3 cobertas em modo demo).

**Comportamento:** lista vazia + aviso explicito *"Modo demo: nao ha
fixture para 'neuro-pediatria'. Disponiveis: ['dermatologia',
'nutrologia', 'ortopedia']"*.

**Onde no codigo:** `pipeline.py:81-86`.

**Teste:** `tests/test_robustez.py::TestEspecialidadeRara::test_especialidade_sem_fixture_em_modo_demo_avisa`.

### B.2 — Especialidade rara em modo producao

**Comportamento (codigo real, fora dos testes):**
1. `gerar_termos()` chama Claude para gerar termos contextualizados;
   se especialidade nao tem termos curados, Claude gera do zero.
2. Sem chave Claude, usa a propria palavra-raiz + variantes (`clinica X`,
   `dr X`, `consultorio X`, etc).
3. Se Ad Library devolver menos de 10 candidatos validos, o `Resultado`
   sai com `lista_incompleta=True` + `justificativa_lista_incompleta`
   detalhada — exatamente o que o enunciado pediu.

**Onde no codigo:** `discovery/search_terms.py:_ampliar_simples` (fallback)
e `pipeline.py:268-279` (justificativa).

**Comprovacao tangivel:** o output `outputs/exemplos/nutrologia__nutrologo-teste.json`
ja mostra esse comportamento — devolveu 9 (nao 10) com justificativa.

### B.3 — Especialidade em caixa mista / com acentos

**Entradas:** `"DermAtoLoGia"`, `"Dermatologia"` (com maiusculas).

**Comportamento:** normalizada com `.strip().lower()` → `"dermatologia"`.
Resultado e o mesmo independente da capitalizacao.

**Teste:** `tests/test_robustez.py::TestEspecialidadeRara::test_especialidade_em_caixa_mista`.

### B.4 — Especialidade vazia

**Entrada:** `""` ou `"   "`.

**Comportamento:** `ValueError("Especialidade vazia.")` antes de
qualquer processamento.

**Teste:** `tests/test_robustez.py::TestEspecialidadeRara::test_especialidade_vazia_e_rejeitada`.

---

## Caso C: "Perfil sem nenhum anuncio"

Tres angulos cobertos.

### C.1 — Candidato com 0 anuncios e filtrado antes do enriquecimento

**Comportamento:** o pipeline tem guarda explicita em `pipeline.py:117-119`:

```python
if cand.n_anuncios_ativos < 1:
    n_descartados_sem_anuncio += 1
    continue
```

Esse candidato:
- NAO chama a API do Claude (economia)
- NAO faz request no Instagram (economia)
- NAO entra na lista final

E ainda incrementa o contador que aparece no relatorio
(`Resultado.n_descartados_sem_anuncio`) para que o avaliador veja o
filtro funcionando.

**Teste:** `tests/test_robustez.py::TestPerfilSemAnuncio::test_candidato_com_zero_anuncios_e_filtrado`.

### C.2 — Cliente passa @ de medico que nao anuncia

**Comportamento:** o @ do cliente NAO precisa anunciar — quem nao
anuncia e justamente quem esta procurando referencia. O pipeline
ignora o status de anuncio do cliente; ele serve apenas para
**excluir-se da lista de referencias** caso aparecer.

**Teste:** `tests/test_robustez.py::TestPerfilSemAnuncio::test_cliente_sem_anuncios_e_buscar_funciona`.

### C.3 — Nenhum candidato bate todos os criterios

**Comportamento:** lista vazia. `Resultado.lista_incompleta=True` com
justificativa completa em `justificativa_lista_incompleta`.

**Teste:** `tests/test_robustez.py::TestEspecialidadeRara::test_especialidade_sem_fixture_em_modo_demo_avisa`
(mesma logica de retorno vazio + justificativa).

---

## Caso D: parser HTML quebrado (defesa em profundidade)

A Meta muda layout da Ad Library sem aviso. Se o parser quebrasse com
HTML inesperado, a ferramenta inteira morreria.

| Entrada                                          | Comportamento esperado |
| ------------------------------------------------ | ---------------------- |
| HTML vazio (`""`)                                | retorna `[]`           |
| HTML quebrado (`"<html>broken<<<"`)              | retorna `[]`           |
| HTML sem `<script>` tags                          | retorna `[]`           |
| `<script>` com JSON invalido                     | retorna `[]` (nao crash) |
| Page_id muito curto (`"123"`)                    | ignorado (anti-falso-positivo) |

**Testes:** `tests/test_robustez.py::TestParserRobustez` (4 testes) +
`tests/test_ad_library_parser.py` (5 testes).

---

## Caso E: comportamento sem chave Claude

**Comportamento:** ferramenta **continua funcionando**. Modos de
degradacao:

| Componente                 | Com Claude              | Sem Claude (fallback)                                |
| -------------------------- | ----------------------- | ---------------------------------------------------- |
| Termos de busca            | Geracao contextual      | Lista curada + variantes simples                     |
| Match de especialidade     | Classificacao few-shot  | Palavras-chave + anti-keywords                       |
| Inferencia de @ IG         | Claude sugere 3, valida | `None` (perfil sai sem handle resolvido)             |

Aviso explicito em `Resultado.avisos`: *"Claude API indisponivel (sem
ANTHROPIC_API_KEY): validacao de especialidade e geracao de termos
usaram heuristicas."*

**Teste:** `tests/test_robustez.py::TestSemChaveClaude::test_pipeline_roda_sem_chave_anthropic`.

---

## Caso F: scorer com dados ausentes

**Cenario:** Instagram bloqueado, nao conseguimos seguidores nem posts.

**Comportamento:** scorer aceita `None` em todos os campos numericos
sem crashar. Aplica **credito parcial** em "postagem recente" para
nao penalizar perfis com IG bloqueado.

**Testes:** `tests/test_robustez.py::TestScorerDadosAusentes` (2 testes)
+ `tests/test_scorer.py` (10 testes).

---

## Resumo: total de testes de robustez

| Categoria                          | Arquivo                                       | Testes |
| ---------------------------------- | --------------------------------------------- | -----: |
| @ que nao existe                   | `test_robustez.py::TestHandleNaoExiste`       | 4      |
| Especialidade rara                 | `test_robustez.py::TestEspecialidadeRara`     | 4      |
| Perfil sem anuncio                 | `test_robustez.py::TestPerfilSemAnuncio`      | 3      |
| Parser HTML robusto                | `test_robustez.py::TestParserRobustez`        | 4      |
| Sem chave Claude                   | `test_robustez.py::TestSemChaveClaude`        | 1      |
| Scorer com dados ausentes          | `test_robustez.py::TestScorerDadosAusentes`   | 2      |
| Bio menciona (None/vazio/emoji)    | `test_robustez.py::TestBioMenciona`           | 6      |
| Limpar handle (URLs, formatos)     | `test_normalize.py::TestLimparHandle`         | 12     |
| Parse de numero (formatos ambig.)  | `test_ig_parser.py::TestParseNumero`          | 12     |
| Parser Ad Library (vazamento, etc) | `test_ad_library_parser.py`                   | 5      |

**Total: 53 testes especificos de robustez** (de 137 testes verdes na suite completa).

---

## Como o avaliador pode reproduzir cada caso

```bash
# Caso A.1: handle invalido
vaipri-ref buscar @@ dermatologia --demo
# → ValueError com mensagem clara

# Caso A.2: handle valido mas inexistente
vaipri-ref buscar @clinica.que.nao.existe.99999 dermatologia --demo
# → roda normalmente, devolve referencias

# Caso B.1: especialidade rara
vaipri-ref buscar @x neurocirurgia --demo
# → aviso "sem fixture", lista vazia

# Caso B.2: especialidade rara em producao (precisa rede + chave)
vaipri-ref buscar @x neurocirurgia
# → Claude gera termos, Ad Library devolve N candidatos,
#   se N < 10 sai com justificativa

# Caso C: perfil cliente sem anuncios
vaipri-ref buscar @cliente.iniciante.zero.ads dermatologia --demo
# → roda normalmente

# Caso E: sem chave Claude
unset ANTHROPIC_API_KEY
vaipri-ref buscar @x dermatologia --demo
# → aviso amarelo, segue com heuristica

# Rodar TODOS os testes de robustez
pytest tests/test_robustez.py -v
```
