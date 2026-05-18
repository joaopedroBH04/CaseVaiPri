"""Scraper publico do Instagram.

Limitacoes assumidas (ver docs/TRADE_OFFS.md):
- Instagram bloqueia acesso a dados detalhados sem login desde 2022.
- Open Graph e Twitter Card meta tags continuam acessiveis e contem
  seguidores, total de posts e nome completo.
- Engajamento real e estimado por benchmark + heuristica.

Saida sempre normalizada como dict com chaves estaveis. Falhas viram
campos None + flag `metricas_completas = False`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}


# Pattern do meta og:description tipico do IG:
#   "12,5 mil Seguidores, 437 Seguindo, 1.234 Posts - Veja..."
# ou em ingles:
#   "12.5K Followers, 437 Following, 1,234 Posts - See Instagram photos..."
_RE_OG = re.compile(
    r"(?P<seguidores>[\d\.\,KkMmBb mil]+?)\s*(?:Seguidores|Followers)"
    r".*?(?P<seguindo>[\d\.\,KkMmBb mil]+?)\s*(?:Seguindo|Following)"
    r".*?(?P<posts>[\d\.\,KkMmBb mil]+?)\s*(?:Posts|Publicacoes)",
    re.IGNORECASE | re.DOTALL,
)

_RE_OG_ALT = re.compile(
    r"(?P<seguidores>[\d\.\,KkMmBb ]+?)\s*Followers"
    r".*?(?P<seguindo>[\d\.\,KkMmBb ]+?)\s*Following"
    r".*?(?P<posts>[\d\.\,KkMmBb ]+?)\s*Posts",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class PerfilIG:
    handle: str
    url: str
    seguidores: int | None = None
    seguindo: int | None = None
    total_posts: int | None = None
    nome_completo: str | None = None
    bio: str | None = None
    foto_url: str | None = None
    metricas_completas: bool = False
    erro: str | None = None


class InstagramScraper:
    def __init__(self, *, cache: Cache, timeout: float = 12.0) -> None:
        self.cache = cache
        self.timeout = timeout

    def buscar_perfil(self, handle: str) -> PerfilIG:
        handle_norm = limpar_handle(handle)
        chave = self.cache.chave("ig_profile", handle_norm)
        cached = self.cache.get(chave)
        if isinstance(cached, dict):
            try:
                return PerfilIG(**cached)
            except Exception:
                pass

        url = url_perfil_ig(handle_norm)
        try:
            html = self._fetch(url)
        except Exception as exc:
            perfil = PerfilIG(handle=handle_norm, url=url, erro=str(exc))
            self.cache.set(chave, perfil.__dict__)
            return perfil

        perfil = _parse_perfil(html, handle_norm, url)
        self.cache.set(chave, perfil.__dict__)
        return perfil

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
    def _fetch(self, url: str) -> str:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=self.timeout) as c:
            r = c.get(url)
            if r.status_code in (301, 302, 303, 307, 308):
                # redirect manual (apesar do follow_redirects, alguns esquemas falham)
                raise RuntimeError(f"Redirect inesperado: {r.status_code}")
            r.raise_for_status()
            if "Login" in r.text and "Sign up" in r.text and "<meta property=\"og:title\"" not in r.text:
                raise RuntimeError("Pagina serviu login wall sem og tags")
            return r.text


def _parse_perfil(html: str, handle: str, url: str) -> PerfilIG:
    soup = BeautifulSoup(html, "lxml")
    og_desc = _meta(soup, "og:description") or _meta(soup, "twitter:description")
    og_title = _meta(soup, "og:title") or _meta(soup, "twitter:title")
    og_image = _meta(soup, "og:image") or _meta(soup, "twitter:image")

    seguidores = seguindo = total_posts = None
    if og_desc:
        m = _RE_OG.search(og_desc) or _RE_OG_ALT.search(og_desc)
        if m:
            seguidores = _parse_numero(m.group("seguidores"))
            seguindo = _parse_numero(m.group("seguindo"))
            total_posts = _parse_numero(m.group("posts"))

    nome_completo: str | None = None
    bio: str | None = None
    if og_title:
        # ex: "Dra. Fulana (@dra.fulana) | Instagram"
        nome_completo = re.split(r"\(@", og_title)[0].strip().strip("|").strip()
    if og_desc and "Veja " in og_desc:
        # texto apos o "-" tipico contem fragmento da bio
        partes = og_desc.split("-", 1)
        if len(partes) == 2:
            bio = partes[1].strip()
    elif og_desc and "See Instagram" in og_desc:
        partes = og_desc.split("-", 1)
        if len(partes) == 2:
            bio = partes[1].strip()

    completas = all(v is not None for v in (seguidores, seguindo, total_posts))

    return PerfilIG(
        handle=handle,
        url=url,
        seguidores=seguidores,
        seguindo=seguindo,
        total_posts=total_posts,
        nome_completo=nome_completo,
        bio=bio,
        foto_url=og_image,
        metricas_completas=completas,
    )


def _meta(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return tag["content"]
    tag = soup.find("meta", attrs={"name": prop})
    if tag and tag.get("content"):
        return tag["content"]
    return None


def _parse_numero(texto: str) -> int | None:
    """Converte '12,5 mil', '1.2K', '1,234' em int.

    Regras (pt-BR primeiro):
    - Sufixo 'mil'/'k' multiplica por 1_000; 'mi'/'m' por 1_000_000; 'bi'/'b' por 1_000_000_000.
    - Quando ha sufixo, o numero pode ter casa decimal: '1,2K' -> 1200; '12,5 mil' -> 12500.
    - Sem sufixo, ponto e virgula sao separadores de milhar: '1.234' -> 1234; '1,234' -> 1234.
    """
    if not texto:
        return None
    s = texto.strip().lower().replace("\xa0", " ").replace(" ", "")

    mult = 1
    if s.endswith("mil"):
        mult = 1_000
        s = s[:-3]
    elif s.endswith("bi"):
        mult = 1_000_000_000
        s = s[:-2]
    elif s.endswith("mi"):
        mult = 1_000_000
        s = s[:-2]
    elif s.endswith("k"):
        mult = 1_000
        s = s[:-1]
    elif s.endswith("m"):
        mult = 1_000_000
        s = s[:-1]
    elif s.endswith("b"):
        mult = 1_000_000_000
        s = s[:-1]

    if mult > 1:
        # Tem sufixo. Em pt-BR a virgula e' decimal; em en o ponto e'.
        # Heuristica: se aparece virgula, ela e' decimal; senao ponto e' decimal.
        if "," in s:
            s_dec = s.replace(".", "").replace(",", ".")
        else:
            s_dec = s
        try:
            return int(round(float(s_dec) * mult))
        except ValueError:
            return None

    # Sem sufixo: ponto e virgula sao separadores de milhar.
    s_int = s.replace(".", "").replace(",", "")
    try:
        return int(s_int)
    except ValueError:
        return None


def estimar_engajamento(seguidores: int | None) -> float | None:
    """Estima taxa de engajamento por faixa de seguidores (benchmarks BR)."""
    if not seguidores or seguidores <= 0:
        return None
    if seguidores < 5_000:
        return 4.0
    if seguidores < 20_000:
        return 2.5
    if seguidores < 100_000:
        return 1.5
    if seguidores < 500_000:
        return 0.9
    return 0.6
