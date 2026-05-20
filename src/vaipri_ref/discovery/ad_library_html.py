"""Contagem oficial de anúncios via página da Ad Library.

A Meta exibe no topo da página de cada anunciante (URL
`view_all_page_id=...`) um texto tipo "~41 resultados" ou
"~XX results". Esse é o número que aparece na Biblioteca quando
o avaliador clica no link.

Aqui fazemos scraping HTTP simples dessa página específica e
extraímos o número via regex. É a fonte mais autoritativa
quando funciona.

Limitações:
- A Meta às vezes bloqueia esse tipo de scraping (especialmente
  em redes corporativas). Por isso esse módulo é COMPLEMENTAR
  ao Apify, não substituto.
- Quando funciona, é mais rápido e gratuito que rodar actor Apify.
"""

from __future__ import annotations

import re
from typing import Iterable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from vaipri_ref.utils.logger import obter as obter_logger


logger = obter_logger()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Padroes do texto "total de resultados" que a Meta exibe no topo:
#   "~41 resultados", "≈ 41 resultados", "Cerca de 41 resultados",
#   "About 41 results", "41 ads".
_REGEXES = [
    # pt-BR variations
    re.compile(r"[~≈≈]\s*(\d[\d.,]*)\s*resultados?", re.IGNORECASE),
    re.compile(r"cerca\s+de\s+(\d[\d.,]*)\s*resultados?", re.IGNORECASE),
    re.compile(r"aproximadamente\s+(\d[\d.,]*)\s*resultados?", re.IGNORECASE),
    # English variations
    re.compile(r"[~≈≈]\s*(\d[\d.,]*)\s*results?", re.IGNORECASE),
    re.compile(r"about\s+(\d[\d.,]*)\s*results?", re.IGNORECASE),
    # JSON embedded in scripts
    re.compile(r'"total_count"\s*:\s*(\d+)'),
    re.compile(r'"adArchiveCount"\s*:\s*(\d+)'),
    re.compile(r'"ad_archive_count"\s*:\s*(\d+)'),
]


def _normalizar_numero(s: str) -> int | None:
    """Converte '41', '1.234', '1,234', '1.5k', '2M' em int."""
    s = s.strip().lower().replace(" ", "")
    if not s:
        return None
    mult = 1
    if s.endswith("k") or s.endswith("mil"):
        mult = 1_000
        s = s[:-3] if s.endswith("mil") else s[:-1]
    elif s.endswith("m") or s.endswith("mi"):
        mult = 1_000_000
        s = s[:-2] if s.endswith("mi") else s[:-1]
    s = s.replace(".", "").replace(",", "")
    try:
        return int(int(s) * mult)
    except (TypeError, ValueError):
        return None


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=False)
def _fetch_html(url: str, timeout: float = 12.0) -> str | None:
    try:
        with httpx.Client(headers=_HEADERS, timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
        if r.status_code != 200:
            return None
        return r.text
    except Exception as exc:
        logger.debug("HTML fetch falhou %s: %s", url, exc)
        return None


def contar_anuncios_via_html(page_id: str, country: str = "BR") -> int | None:
    """Tenta extrair '~XX resultados' do HTML da pagina do anunciante.

    Retorna o numero quando consegue, None caso contrario.
    """
    if not page_id or not page_id.isdigit():
        return None

    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all"
        f"&country={country}&view_all_page_id={page_id}"
        f"&media_type=all"
    )
    html = _fetch_html(url)
    if not html:
        return None

    # Procura primeiro pelos padroes mais especificos (JSON)
    for regex in _REGEXES:
        m = regex.search(html)
        if m:
            n = _normalizar_numero(m.group(1))
            if n is not None and 0 <= n <= 10000:
                logger.debug("HTML contagem para %s: %d (regex %s)", page_id, n, regex.pattern[:40])
                return n
    return None


def contar_anuncios_via_html_batch(
    page_ids: Iterable[str], country: str = "BR"
) -> dict[str, int]:
    """Tenta extrair contagem oficial para uma lista de page_ids.

    Sequencial pra nao disparar throttling. Falhas individuais nao
    quebram o batch — paginas que nao retornaram numero ficam de fora
    do dict.
    """
    out: dict[str, int] = {}
    for pid in page_ids:
        n = contar_anuncios_via_html(pid, country=country)
        if n is not None:
            out[pid] = n
    if out:
        logger.info("HTML contagem: %d de %d paginas via scraping direto", len(out), len(list(page_ids)))
    return out
