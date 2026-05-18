"""Resolve o handle do Instagram a partir de uma pagina Facebook ou nome.

Ordem de tentativa:
1. Se o candidato ja trouxe `instagram_handle_hint`, valida e usa.
2. Se temos URL da FB Page, faz scraping leve buscando link `instagram.com/...`.
3. Se nada disso funciona, pede inferencia ao Claude a partir do nome.
   Cada handle inferido e validado por HEAD request antes de aceitar.
"""

from __future__ import annotations

import re
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


@dataclass
class HandleResolvido:
    handle: str | None
    confianca: Literal["alta", "media", "baixa"]
    fonte: str  # "hint", "fb_page", "claude_inferencia", None


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
        # Em modo demo, o hint vem da fixture e nao queremos bater no IG real.
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

        # 1) hint direto da Ad Library / fixture
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

        # 2) buscar link na pagina Facebook publica
        if fb_page_url:
            handle_via_fb = self._buscar_via_fb_page(fb_page_url)
            if handle_via_fb:
                res = HandleResolvido(handle=handle_via_fb, confianca="alta", fonte="fb_page")
                self.cache.set(chave, res.__dict__)
                return res

        # 3) inferir com Claude
        handle_inferido = self._inferir_com_claude(fb_page_name)
        if handle_inferido:
            res = HandleResolvido(handle=handle_inferido, confianca="media", fonte="claude_inferencia")
            self.cache.set(chave, res.__dict__)
            return res

        res = HandleResolvido(handle=None, confianca="baixa", fonte="nenhum")
        self.cache.set(chave, res.__dict__)
        return res

    # --------- helpers ---------

    def _valida(self, handle: str) -> bool:
        url = url_perfil_ig(handle)
        try:
            with httpx.Client(headers=_HEADERS, timeout=8.0, follow_redirects=True) as c:
                r = c.head(url)
                if r.status_code == 405:  # alguns nodes nao suportam HEAD
                    r = c.get(url)
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
