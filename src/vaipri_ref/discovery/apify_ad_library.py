"""Adapter Apify Ad Library -> nosso formato interno (_AdvertiserBruto).

Apify retorna anuncios individuais; agregamos por page_id pra
saber quantos anuncios ativos cada anunciante tem. Tambem
extraimos o handle Instagram quando o actor consegue capturar.
"""

from __future__ import annotations

from typing import Any

from vaipri_ref.discovery.apify_client import ApifyClient, ApifyError
from vaipri_ref.utils.logger import obter as obter_logger


logger = obter_logger()


def _normalizar_anuncio(raw: dict[str, Any]) -> dict[str, Any]:
    """Normaliza chaves do actor para nosso shape canonico.

    Tenta varias variacoes de nome (actors diferentes usam chaves
    diferentes) e devolve um dict simples.
    """
    def first(*keys):
        for k in keys:
            v = raw.get(k)
            if v is not None and v != "":
                return v
        return None

    return {
        "page_id":        str(first("pageId", "page_id", "page", "advertiserId") or ""),
        "page_name":      str(first("pageName", "page_name", "advertiserName") or ""),
        "ad_archive_id":  str(first("adArchiveId", "ad_archive_id", "id") or ""),
        "snapshot_url":   first("snapshotUrl", "snapshot_url", "url"),
        "link_url":       first("linkUrl", "link_url", "ad_creative_link_caption"),
        "ig_username":    first("igUsername", "ig_username", "instagramUsername"),
        "start_date":     first("startDate", "start_date", "ad_delivery_start_time"),
        "end_date":       first("endDate", "end_date", "ad_delivery_stop_time"),
    }


def buscar_anunciantes(
    client: ApifyClient,
    termo: str,
    *,
    country: str = "BR",
    max_resultados: int = 50,
) -> list[dict[str, Any]]:
    """Busca termos na Ad Library via Apify e agrega por page_id.

    Retorna lista de dicts:
        {
          "page_id": str,
          "page_name": str,
          "n_anuncios": int,
          "ig_handle_hint": str | None,
          "ad_snapshot_urls": list[str],
        }
    """
    try:
        items = client.buscar_ad_library(
            termo,
            country=country,
            max_resultados=max_resultados,
            somente_ativos=True,
        )
    except ApifyError as exc:
        logger.warning("Apify Ad Library falhou em %r: %s", termo, exc)
        return []

    if not items:
        return []

    agregado: dict[str, dict[str, Any]] = {}
    for item in items:
        normalizado = _normalizar_anuncio(item)
        pid = normalizado["page_id"]
        if not pid:
            continue
        if pid not in agregado:
            agregado[pid] = {
                "page_id": pid,
                "page_name": normalizado["page_name"] or f"Page {pid}",
                "n_anuncios": 1,
                "ig_handle_hint": normalizado["ig_username"],
                "ad_snapshot_urls": [normalizado["snapshot_url"]] if normalizado["snapshot_url"] else [],
            }
        else:
            cur = agregado[pid]
            cur["n_anuncios"] += 1
            if not cur["ig_handle_hint"] and normalizado["ig_username"]:
                cur["ig_handle_hint"] = normalizado["ig_username"]
            if normalizado["snapshot_url"]:
                cur["ad_snapshot_urls"].append(normalizado["snapshot_url"])
            # Atualiza nome se o anterior era generico
            if (cur["page_name"] or "").startswith("Page ") and normalizado["page_name"]:
                cur["page_name"] = normalizado["page_name"]

    logger.info("Apify Ad Library: termo %r -> %d anuncios -> %d paginas",
                termo, len(items), len(agregado))
    return list(agregado.values())


def contar_anuncios_de_paginas(
    client: ApifyClient,
    page_ids: list[str],
    *,
    country: str = "BR",
    max_por_pagina: int = 200,
) -> dict[str, int]:
    """Conta o TOTAL REAL de anuncios ativos por page_id.

    Necessario porque a busca por termo so' retorna anuncios que mencionam
    aquele termo — nao o total da pagina. Por exemplo, uma dermato pode
    ter 25 anuncios ativos mas so' 5 mencionam 'dermatologia'.

    Faz UMA UNICA chamada Apify com URLs especificas de cada pagina
    (formato `view_all_page_id=...`), agregando os resultados.

    Retorna dict {page_id: n_anuncios_ativos}. Paginas sem anuncios
    ativos ou nao encontradas nao aparecem no dict.
    """
    if not page_ids:
        return {}

    # Dedup mantendo ordem
    page_ids = list(dict.fromkeys(page_ids))

    urls = [
        {
            "url": (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=active&ad_type=all"
                f"&country={country}&view_all_page_id={pid}"
                f"&media_type=all"
            )
        }
        for pid in page_ids
    ]

    run_input = {
        "urls": urls,
        "count": max_por_pagina,
        "scrapeAdDetails": False,  # so contagem, nao precisamos do conteudo
        "scrapePageAds.activeStatus": "active",
    }

    try:
        items = client._run_sync(client._cfg.ad_library_actor, run_input)
    except ApifyError as exc:
        logger.warning("Apify contagem por pagina falhou: %s", exc)
        return {}

    contagem: dict[str, int] = {}
    for item in items:
        normalizado = _normalizar_anuncio(item)
        pid = normalizado.get("page_id")
        if not pid:
            continue
        contagem[pid] = contagem.get(pid, 0) + 1

    logger.info(
        "Apify contagem por pagina: %d paginas solicitadas, %d com anuncios contados",
        len(page_ids), len(contagem),
    )
    return contagem
