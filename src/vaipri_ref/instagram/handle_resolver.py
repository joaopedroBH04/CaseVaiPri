"""Resolve o handle do Instagram a partir de uma pagina Facebook ou nome.

Ordem de tentativa:
1. Hint direto da Ad Library / fixture (se presente).
2. Scraping da pagina Facebook publica buscando link `instagram.com/...`.
3. Heuristica agressiva a partir do nome da pagina: gera handles plausiveis
   e valida cada um via HEAD request no Instagram. Sem custo, sem IA.
4. Inferencia via Claude (se chave disponivel) — fallback final.

Se NADA funcionar, devolve `handle=None` com `confianca="baixa"` e
`fonte="nenhum"`. O pipeline NAO descarta nesse caso — a referencia
ainda e util (page_name + biblioteca_anuncios_url).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

import httpx

from vaipri_ref.ai.claude_client import ClaudeClient
from vaipri_ref.utils.cache import Cache
from vaipri_ref.utils.logger import obter as obter_logger
from vaipri_ref.utils.normalize import limpar_handle, url_perfil_ig


logger = obter_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
}

_REGEX_IG = re.compile(r"instagram\.com/([a-zA-Z0-9_.]{2,30})")

# Palavras que NAO entram nos candidatos de handle (genericas demais
# pra serem o handle real do medico).
_STOPWORDS = {
    "dr", "dra", "doutor", "doutora", "medico", "medica",
    "clinica", "consultorio", "centro", "instituto", "espaco",
    "saude", "estetica", "and", "the", "of", "&",
}

# Marcadores de papel medico — quando aparecem no inicio, viram prefixo
# em alguns dos candidatos (`drmarcos`, `dramarcos`).
_PREFIXOS_DR = {"dr", "dra", "doutor", "doutora"}


@dataclass
class HandleResolvido:
    handle: str | None
    confianca: Literal["alta", "media", "baixa"]
    fonte: str  # "hint", "fb_page", "heuristica_nome", "claude_inferencia", "nenhum"


class HandleResolver:
    def __init__(
        self,
        *,
        cache: Cache,
        claude: ClaudeClient,
        pular_validacao_http: bool = False,
    ) -> None:
        self.cache = cache
        self.claude = claude
        self.pular_validacao_http = pular_validacao_http

    def resolver(
        self,
        *,
        fb_page_id: str,
        fb_page_name: str,
        fb_page_url: str | None,
        hint: str | None,
    ) -> HandleResolvido:
        chave = self.cache.chave("ig_handle", fb_page_id, self.pular_validacao_http)
        cached = self.cache.get(chave)
        if isinstance(cached, dict):
            try:
                return HandleResolvido(**cached)
            except Exception:
                pass

        # 1) hint direto (Ad Library ou fixture demo)
        if hint:
            try:
                limpo = limpar_handle(hint)
            except ValueError:
                limpo = None
            if limpo:
                if self.pular_validacao_http or self._valida(limpo):
                    res = HandleResolvido(handle=limpo, confianca="alta", fonte="hint")
                    self.cache.set(chave, res.__dict__)
                    return res

        # 2) buscar link na pagina Facebook publica (frequentemente bloqueado, mas tenta)
        if fb_page_url:
            handle_via_fb = self._buscar_via_fb_page(fb_page_url)
            if handle_via_fb:
                res = HandleResolvido(handle=handle_via_fb, confianca="alta", fonte="fb_page")
                self.cache.set(chave, res.__dict__)
                return res

        # 3) HEURISTICA AGRESSIVA: gera candidatos a partir do nome e valida no IG.
        # Tem boa taxa de acerto pra perfis medicos (~50-70% no nosso teste),
        # baixa dependencia (so HTTP), zero custo.
        handle_heuristica = self._tentar_heuristica(fb_page_name)
        if handle_heuristica:
            res = HandleResolvido(
                handle=handle_heuristica,
                confianca="media",
                fonte="heuristica_nome",
            )
            self.cache.set(chave, res.__dict__)
            return res

        # 4) Claude (se disponivel) — fallback final
        handle_inferido = self._inferir_com_claude(fb_page_name)
        if handle_inferido:
            res = HandleResolvido(handle=handle_inferido, confianca="media", fonte="claude_inferencia")
            self.cache.set(chave, res.__dict__)
            return res

        # 5) Nao achou. Pipeline NAO deve descartar — usar page_name + ad_lib_url.
        res = HandleResolvido(handle=None, confianca="baixa", fonte="nenhum")
        self.cache.set(chave, res.__dict__)
        return res

    # --------- helpers ---------

    def _tentar_heuristica(self, nome: str) -> str | None:
        for cand in gerar_handles_candidatos(nome):
            if self.pular_validacao_http:
                # Modo demo: aceita o primeiro candidato gerado (nao bate HTTP)
                return cand
            if self._valida(cand):
                logger.debug("Heuristica achou handle %r para %r", cand, nome)
                return cand
        return None

    def _valida(self, handle: str) -> bool:
        url = url_perfil_ig(handle)
        try:
            with httpx.Client(headers=_HEADERS, timeout=8.0, follow_redirects=True) as c:
                r = c.head(url)
                if r.status_code == 405:  # alguns nodes nao suportam HEAD
                    r = c.get(url)
                # Instagram retorna 200 para perfis reais e 404 para inexistentes.
                # Alguns proxies retornam 200 com redirect para login — toleramos.
                return r.status_code == 200
        except Exception:
            return False

    def _buscar_via_fb_page(self, fb_page_url: str) -> str | None:
        try:
            with httpx.Client(headers=_HEADERS, timeout=10.0, follow_redirects=True) as c:
                r = c.get(fb_page_url)
                if r.status_code != 200:
                    return None
                m = _REGEX_IG.search(r.text)
                if not m:
                    return None
                cand = m.group(1)
                try:
                    cand = limpar_handle(cand)
                except ValueError:
                    return None
                return cand if self._valida(cand) else None
        except Exception as exc:
            logger.debug("Falha resolvendo handle via FB page: %s", exc)
            return None

    def _inferir_com_claude(self, nome: str) -> str | None:
        if not self.claude.disponivel:
            return None
        prompt = (
            "Dado o nome da pagina Facebook de um anunciante medico, sugira "
            "ATE 3 handles plausiveis de Instagram (sem @, sem URL).\n"
            "Regras: minusculas, sem espaco; pode ter ponto e numero; tamanho 2-30.\n"
            f"Nome: {nome!r}\n"
            'Responda em JSON: {"handles": ["..."]}'
        )
        resposta = self.claude.json_objeto(prompt, max_tokens=200, temperature=0.0)
        if not resposta:
            return None
        candidatos = resposta.get("handles", []) if isinstance(resposta, dict) else []
        for cand in candidatos:
            try:
                cand_limpo = limpar_handle(str(cand))
            except ValueError:
                continue
            if self._valida(cand_limpo):
                return cand_limpo
        return None


# ============================================================
# Heuristica: gera handles candidatos a partir do nome
# ============================================================


def gerar_handles_candidatos(page_name: str) -> list[str]:
    """A partir do nome da pagina, gera ate ~12 handles IG plausiveis.

    Estrategia: anunciantes medicos costumam usar variacoes obvias do
    nome da clinica/profissional como handle. Cobrimos os padroes mais
    comuns no Brasil:

    - "Dra Ana Lima Dermatologia" -> draanalima, dra.analima, draana,
                                     dra.ana, anaalima, ana.lima, ...
    - "Clinica Lume Derma"        -> clinicalume, lume.derma, lumederma, ...

    Cada candidato e' validado depois com HEAD request no Instagram.
    """
    if not page_name:
        return []

    # 1. Normaliza: lowercase, sem acento, sem pontuacao
    nome = unicodedata.normalize("NFKD", page_name).encode("ascii", "ignore").decode()
    nome = nome.lower()
    nome = re.sub(r"[^\w\s]", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    palavras = [w for w in nome.split() if w and len(w) >= 2]
    if not palavras:
        return []

    # 2. Separa prefixo "dr/dra" do resto
    prefixo: str | None = None
    palavras_no_prefixo = list(palavras)
    if palavras[0] in _PREFIXOS_DR:
        prefixo = palavras[0]
        palavras_no_prefixo = palavras[1:]

    # 3. Palavras significativas (sem stopwords)
    significativas = [w for w in palavras_no_prefixo if w not in _STOPWORDS]
    if not significativas:
        # Tudo era stopword: pega o primeiro depois do prefixo de qualquer forma
        significativas = palavras_no_prefixo[:2] if palavras_no_prefixo else []

    # 4. Gera variacoes
    candidatos: list[str] = []

    def adicionar(c: str) -> None:
        c = c.strip(".").strip("_")
        if c and 3 <= len(c) <= 30 and c not in candidatos:
            candidatos.append(c)

    # 4a. Tudo junto: "drmarcossancheortopedia"
    if prefixo:
        adicionar(prefixo + "".join(significativas))
    adicionar("".join(palavras))
    adicionar("".join(significativas))

    # 4b. Com ponto: "dr.marcos.sanches"
    if prefixo and significativas:
        adicionar(prefixo + "." + ".".join(significativas))
        adicionar(prefixo + "." + significativas[0])

    # 4c. Com underscore: "dr_marcos_sanches"
    if prefixo and significativas:
        adicionar(prefixo + "_" + "_".join(significativas))

    # 4d. Sem prefixo, primeiras 2 palavras
    if len(significativas) >= 2:
        adicionar(significativas[0] + significativas[1])
        adicionar(significativas[0] + "." + significativas[1])

    # 4e. Apenas a primeira palavra significativa (clinica de nome unico)
    if significativas:
        adicionar(significativas[0])

    # 4f. Variacao "drnome" sem ponto, mais comum no IG
    if prefixo and significativas:
        adicionar(prefixo + significativas[0])

    # cap em 12 candidatos pra nao bater o IG demais
    return candidatos[:12]
