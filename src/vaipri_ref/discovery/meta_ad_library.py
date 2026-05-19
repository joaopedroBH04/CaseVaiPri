"""Scraper da Biblioteca de Anuncios da Meta (Brasil).

Estrategia de duas camadas:

1. **Caminho rapido (HTTP):** baixa o HTML inicial da URL publica da
   Ad Library com `httpx`. A pagina serve um JSON embedded em `<script>`
   contendo os primeiros ~30 resultados. Esse caminho cobre ~80% dos
   casos sem precisar de browser.

2. **Caminho robusto (Playwright):** quando o HTML inicial nao tem o JSON
   (Meta serviu pagina de "carregando"), abre Playwright em modo headless,
   espera os cards renderizarem e extrai do DOM.

Apenas os campos necessarios para o pipeline sao extraidos. Cada
candidato carrega: page_id, page_name, n_anuncios_ativos, hint do IG.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from vaipri_ref.models import Candidato
from vaipri_ref.utils.cache import Cache
from vaipri_ref.utils.logger import obter as obter_logger
from vaipri_ref.utils.normalize import url_busca_biblioteca


logger = obter_logger()

_HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}

# Regex que pesca o blob JSON com a chave que prefixa os resultados de busca.
# A Meta usa varios nomes ao longo do tempo: search_results_connection,
# adLibraryMainSearchResult, etc. Cobrimos os principais.
_REGEX_BLOBS = [
    re.compile(r'"search_results_connection"\s*:\s*({.*?"page_info".*?})', re.DOTALL),
    re.compile(r'"results_connection"\s*:\s*({.*?"page_info".*?})', re.DOTALL),
    re.compile(r'"adLibraryMainSearchResult"\s*:\s*({.*?})\s*,\s*"adLibrary', re.DOTALL),
]

# Pesca um link de instagram dentro do JSON do anunciante.
_REGEX_IG = re.compile(r"instagram\.com/([a-zA-Z0-9_.]{2,30})")


@dataclass
class _AdvertiserBruto:
    fb_page_id: str
    fb_page_name: str
    n_anuncios_ativos: int = 0
    ig_handle_hint: str | None = None
    fb_page_url: str | None = None


class MetaAdLibraryScraper:
    def __init__(
        self,
        *,
        cache: Cache,
        country: str = "BR",
        headless: bool = True,
        max_termo_timeout_s: int = 25,
        graph_api_token: str | None = None,
    ) -> None:
        self.cache = cache
        self.country = country
        self.headless = headless
        self.timeout = max_termo_timeout_s
        # Quando ha token, o caminho preferido e a Graph API oficial.
        # Funciona em qualquer rede (nao depende do IP ser aceito pela
        # UI publica do facebook.com).
        self._graph: "MetaGraphAPI | None" = None
        if graph_api_token:
            from vaipri_ref.discovery.meta_graph_api import MetaGraphAPI
            self._graph = MetaGraphAPI(access_token=graph_api_token, country=country)

    @property
    def usando_graph_api(self) -> bool:
        return self._graph is not None

    # ------------- API publica ----------------

    def buscar(self, termos: list[str], limite_por_termo: int = 12) -> list[Candidato]:
        """Roda buscas para todos os termos e devolve candidatos deduplicados.

        Importante: `termo_busca_origem` e' rastreado por candidato.
        Esse campo serve como EVIDENCIA de especialidade: se a Meta
        retornou um anunciante para o termo 'dermatologista', ele
        provavelmente e' dermato — mesmo que o nome FB nao mencione.
        """
        agregados: dict[str, _AdvertiserBruto] = {}
        origem: dict[str, str] = {}  # page_id -> primeiro termo que retornou esse anunciante
        for termo in termos:
            try:
                lote = self._buscar_termo(termo, limite=limite_por_termo)
            except Exception as exc:
                logger.warning("Falha buscando termo %r: %s", termo, exc)
                continue
            logger.info(
                "Termo %r -> %d anunciantes brutos",
                termo,
                len(lote),
            )
            for adv in lote:
                if adv.fb_page_id not in agregados:
                    agregados[adv.fb_page_id] = adv
                    origem[adv.fb_page_id] = termo  # primeiro termo que achou
                else:
                    cur = agregados[adv.fb_page_id]
                    cur.n_anuncios_ativos = max(cur.n_anuncios_ativos, adv.n_anuncios_ativos)
                    if not cur.ig_handle_hint and adv.ig_handle_hint:
                        cur.ig_handle_hint = adv.ig_handle_hint

        candidatos: list[Candidato] = []
        for adv in agregados.values():
            try:
                candidatos.append(
                    Candidato(
                        fb_page_id=adv.fb_page_id,
                        fb_page_name=adv.fb_page_name,
                        fb_page_url=adv.fb_page_url,  # pydantic valida URL
                        n_anuncios_ativos=adv.n_anuncios_ativos,
                        instagram_handle_hint=adv.ig_handle_hint,
                        termo_busca_origem=origem.get(adv.fb_page_id),
                    )
                )
            except Exception as exc:
                logger.debug("Descartando candidato invalido %s: %s", adv.fb_page_id, exc)
        candidatos.sort(key=lambda c: c.n_anuncios_ativos, reverse=True)
        return candidatos

    # ------------- caminhos ----------------

    def _buscar_termo(self, termo: str, *, limite: int) -> list[_AdvertiserBruto]:
        chave = self.cache.chave("ad_library", self.country, termo, bool(self._graph))
        cached = self.cache.get(chave)
        if cached is not None:
            try:
                return [_AdvertiserBruto(**c) for c in cached]
            except Exception:
                pass

        resultado: list[_AdvertiserBruto] = []

        # Caminho 1 (preferido): Graph API oficial — funciona em qualquer rede.
        if self._graph is not None:
            try:
                anuncios = self._graph.buscar_termo(termo, limite=limite * 3)
                agregado = self._graph.agrupar_por_pagina(anuncios)
                for page_id, page_name, n in agregado:
                    resultado.append(
                        _AdvertiserBruto(
                            fb_page_id=page_id,
                            fb_page_name=page_name,
                            n_anuncios_ativos=n,
                        )
                    )
                logger.info("Graph API: termo %r -> %d paginas", termo, len(resultado))
            except Exception as exc:
                logger.warning("Graph API falhou em %r (%s); caindo pro scraping web", termo, exc)
                resultado = []

        # Caminho 2 (fallback): scraping da UI publica.
        if not resultado:
            url = url_busca_biblioteca(termo, country=self.country)
            try:
                resultado = _scrape_rapido_http(url) or []
            except Exception as exc:
                logger.debug("HTTP rapido falhou (%s); caindo pro Playwright", exc)
                resultado = []

            if not resultado:
                try:
                    resultado = asyncio.run(
                        _scrape_playwright(url, headless=self.headless, timeout_s=self.timeout)
                    )
                except Exception as exc:
                    logger.warning("Playwright tambem falhou: %s", exc)
                    resultado = []

        # ============================================================
        # ENRIQUECIMENTO: substitui nomes genericos por nomes REAIS via
        # Graph API endpoint /{page_id} (que e' mais permissivo que
        # ads_archive — funciona sem App Review).
        # ============================================================
        if self._graph is not None and resultado:
            enriquecidos = 0
            for adv in resultado:
                # Detecta nome generico do scraper: "Page 12345" quando page_name
                # nao foi capturado no HTML inicial.
                if adv.fb_page_name and adv.fb_page_name.startswith("Page "):
                    nome_real = self._graph.obter_nome_pagina(adv.fb_page_id)
                    if nome_real:
                        adv.fb_page_name = nome_real
                        enriquecidos += 1
            if enriquecidos:
                logger.info(
                    "Termo %r: %d nomes enriquecidos via Graph /page",
                    termo, enriquecidos
                )

        resultado = resultado[:limite]
        self.cache.set(chave, [r.__dict__ for r in resultado])
        return resultado


# ============== caminho rapido (HTTP) ==============


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def _scrape_rapido_http(url: str) -> list[_AdvertiserBruto]:
    with httpx.Client(headers=_HEADERS_BASE, follow_redirects=True, timeout=20.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    return _parse_html(html)


def _parse_html(html: str) -> list[_AdvertiserBruto]:
    soup = BeautifulSoup(html, "lxml")
    scripts = soup.find_all("script")
    advertisers: dict[str, _AdvertiserBruto] = {}
    for s in scripts:
        if not s.string:
            continue
        bloco = s.string
        # Procura por padroes de page com numero de anuncios ativos no JSON serializado.
        for adv in _extrair_pages_de_blob(bloco):
            if adv.fb_page_id and adv.fb_page_id not in advertisers:
                advertisers[adv.fb_page_id] = adv
            elif adv.fb_page_id:
                cur = advertisers[adv.fb_page_id]
                cur.n_anuncios_ativos = max(cur.n_anuncios_ativos, adv.n_anuncios_ativos)
                if not cur.ig_handle_hint and adv.ig_handle_hint:
                    cur.ig_handle_hint = adv.ig_handle_hint
    return list(advertisers.values())


# Padroes que costumam aparecer na resposta JSON serializada.
# - "page_id":"12345..."
# - "page_name":"Dr ..."
# - "page_profile_uri":"https://facebook.com/..."
# - "ig_username":"..." (raro mas existe)
# - "total_ads": numero, ou "active_ads_count"
_PAT_PAGE_ID = re.compile(r'"page_id"\s*:\s*"(\d{6,})"')
_PAT_NAME = re.compile(r'"page_name"\s*:\s*"([^"\\]{2,200})"')
_PAT_URI = re.compile(r'"page_profile_uri"\s*:\s*"([^"\\]+)"')
_PAT_TOTAL = re.compile(r'"total_active_ads"\s*:\s*(\d+)')
_PAT_TOTAL2 = re.compile(r'"page_ads_count"\s*:\s*(\d+)')
_PAT_IG = re.compile(r'"ig_username"\s*:\s*"([^"\\]+)"')


def _extrair_pages_de_blob(blob: str) -> list[_AdvertiserBruto]:
    """Procura objetos JSON contendo `page_id` e extrai os campos vizinhos.

    Estrategia: para cada match de `page_id`, define uma janela `[ini, fim]`
    delimitada pelo proximo page_id (para nao "vazar" para o card seguinte).
    Busca os outros campos APENAS dentro dessa janela.
    """
    out: list[_AdvertiserBruto] = []
    matches = list(_PAT_PAGE_ID.finditer(blob))
    if not matches:
        return out

    for i, m in enumerate(matches):
        pid = m.group(1)
        ini = m.end()
        # fim = inicio do proximo page_id (corta o vazamento) ou ate +4000 chars
        if i + 1 < len(matches):
            fim = min(matches[i + 1].start(), ini + 4000)
        else:
            fim = min(len(blob), ini + 4000)
        janela = blob[ini:fim]

        nome_match = _PAT_NAME.search(janela)
        uri_match = _PAT_URI.search(janela)
        total_match = _PAT_TOTAL.search(janela) or _PAT_TOTAL2.search(janela)
        ig_match = _PAT_IG.search(janela)
        if not ig_match:
            inline = _REGEX_IG.search(janela)
            if inline:
                ig_match = inline

        nome = nome_match.group(1) if nome_match else f"Page {pid}"
        try:
            nome = json.loads(f'"{nome}"')
        except Exception:
            pass

        out.append(
            _AdvertiserBruto(
                fb_page_id=pid,
                fb_page_name=nome.strip(),
                fb_page_url=(uri_match.group(1).replace("\\/", "/") if uri_match else None),
                n_anuncios_ativos=int(total_match.group(1)) if total_match else 1,
                ig_handle_hint=(ig_match.group(1) if ig_match else None),
            )
        )
    return out


# ============== caminho robusto (Playwright) ==============


async def _scrape_playwright(url: str, *, headless: bool, timeout_s: int) -> list[_AdvertiserBruto]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        logger.warning("Playwright nao instalado: %s", exc)
        return []

    advertisers: dict[str, _AdvertiserBruto] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        try:
            ctx = await browser.new_context(
                user_agent=_HEADERS_BASE["User-Agent"],
                locale="pt-BR",
                viewport={"width": 1366, "height": 900},
            )
            page = await ctx.new_page()

            # Intercepta respostas JSON para extrair dados sem depender do DOM.
            jsons_capturados: list[str] = []

            async def handle_response(response: Any) -> None:
                ct = response.headers.get("content-type", "")
                if "json" in ct and "facebook.com" in response.url:
                    try:
                        body = await response.text()
                        if "page_id" in body or "page_name" in body:
                            jsons_capturados.append(body)
                    except Exception:
                        pass

            page.on("response", handle_response)

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            # da tempo do JS hidratar
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout_s * 1000)
            except Exception:
                pass

            # tenta scroll para forcar lazy load
            for _ in range(2):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1.2)

            html = await page.content()
            for adv in _parse_html(html):
                advertisers.setdefault(adv.fb_page_id, adv)

            for body in jsons_capturados:
                for adv in _extrair_pages_de_blob(body):
                    advertisers.setdefault(adv.fb_page_id, adv)
        finally:
            await browser.close()

    return list(advertisers.values())
