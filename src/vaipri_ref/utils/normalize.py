"""Normalizacao de handles, URLs e strings de entrada."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote_plus, urlencode


_HANDLE_RE = re.compile(r"^[a-zA-Z0-9_.]{1,30}$")
_INSTAGRAM_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?", re.I)


def limpar_handle(entrada: str) -> str:
    """Normaliza '@dra.fulana', 'https://instagram.com/dra.fulana/' e variantes para 'dra.fulana'.

    >>> limpar_handle('@DRA.FULANA')
    'dra.fulana'
    >>> limpar_handle('https://www.instagram.com/dra.fulana/')
    'dra.fulana'
    >>> limpar_handle('dra.fulana')
    'dra.fulana'
    """
    if not entrada:
        raise ValueError("handle vazio")

    valor = entrada.strip().lower()

    match = _INSTAGRAM_URL_RE.search(valor)
    if match:
        valor = match.group(1)

    valor = valor.lstrip("@")
    valor = valor.rstrip("/")

    if not _HANDLE_RE.match(valor):
        raise ValueError(f"handle invalido: {entrada!r}")
    return valor


def url_perfil_ig(handle: str) -> str:
    handle = limpar_handle(handle)
    return f"https://www.instagram.com/{handle}/"


def url_biblioteca_anuncios(fb_page_id: str, country: str = "BR") -> str:
    """URL canonica da Biblioteca de Anuncios para uma pagina especifica."""
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": country,
        "view_all_page_id": fb_page_id,
        "media_type": "all",
    }
    return "https://www.facebook.com/ads/library/?" + urlencode(params)


def url_busca_biblioteca(termo: str, country: str = "BR") -> str:
    """URL de busca por keyword na Biblioteca de Anuncios."""
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": country,
        "media_type": "all",
        "q": termo,
        "search_type": "keyword_unordered",
    }
    return "https://www.facebook.com/ads/library/?" + urlencode(params)


def slug(texto: str) -> str:
    """Slug ASCII para nome de arquivo."""
    nfkd = unicodedata.normalize("NFKD", texto)
    so_ascii = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    so_ascii = re.sub(r"[^a-z0-9]+", "-", so_ascii).strip("-")
    return so_ascii or "saida"


def encode_termo(termo: str) -> str:
    return quote_plus(termo)
