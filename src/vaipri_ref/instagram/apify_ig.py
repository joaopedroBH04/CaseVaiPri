"""Adapter Apify Instagram Profile Scraper -> PerfilIG.

Pega de uma lista de handles os dados de cada perfil:
seguidores, engajamento real (likes+comentarios dos ultimos posts /
seguidores), bio, posts recentes, foto.

Esse e o caminho que destrava as metricas pedidas pelo enunciado.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from vaipri_ref.discovery.apify_client import ApifyClient, ApifyError
from vaipri_ref.instagram.scraper import PerfilIG
from vaipri_ref.utils.logger import obter as obter_logger


logger = obter_logger()


def _coletar_int(d: dict[str, Any], *keys: str) -> int | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def _coletar_str(d: dict[str, Any], *keys: str) -> str | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _calcular_engajamento(seguidores: int | None, latest_posts: list[dict[str, Any]] | None) -> float | None:
    """Engajamento medio = media de (likes + comentarios) / seguidores * 100.

    Usa os ultimos posts disponiveis (a Apify costuma trazer 12).
    """
    if not seguidores or not latest_posts:
        return None
    interacoes = []
    for p in latest_posts:
        likes = _coletar_int(p, "likesCount", "likes") or 0
        comments = _coletar_int(p, "commentsCount", "comments") or 0
        total = likes + comments
        if total > 0:
            interacoes.append(total)
    if not interacoes:
        return None
    media = sum(interacoes) / len(interacoes)
    return round((media / seguidores) * 100, 2)


def _contar_posts_30d(latest_posts: list[dict[str, Any]] | None) -> int | None:
    if not latest_posts:
        return None
    limite = datetime.now(timezone.utc) - timedelta(days=30)
    contagem = 0
    for p in latest_posts:
        ts = _coletar_str(p, "timestamp", "takenAtTimestamp", "createdAt")
        if not ts:
            continue
        try:
            # Apify costuma usar ISO 8601 (com Z)
            ts_clean = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= limite:
                contagem += 1
        except ValueError:
            continue
    return contagem


def _parse_perfil_apify(raw: dict[str, Any]) -> PerfilIG:
    handle = (_coletar_str(raw, "username") or "").lstrip("@").lower()
    seguidores = _coletar_int(raw, "followersCount", "followers")
    seguindo = _coletar_int(raw, "followsCount", "following")
    total_posts = _coletar_int(raw, "postsCount", "posts")
    nome = _coletar_str(raw, "fullName", "name")
    bio = _coletar_str(raw, "biography", "bio")
    foto = _coletar_str(raw, "profilePicUrl", "profilePicUrlHD", "profilePic")
    latest_posts = raw.get("latestPosts") or raw.get("posts") or []
    engajamento = _calcular_engajamento(seguidores, latest_posts)
    posts_30d = _contar_posts_30d(latest_posts)

    perfil = PerfilIG(
        handle=handle,
        url=f"https://www.instagram.com/{handle}/",
        seguidores=seguidores,
        seguindo=seguindo,
        total_posts=total_posts,
        posts_ultimos_30_dias=posts_30d,
        nome_completo=nome,
        bio=bio,
        foto_url=foto,
        metricas_completas=all(v is not None for v in (seguidores, total_posts, engajamento)),
    )
    return perfil


def enriquecer_perfis(
    client: ApifyClient,
    handles: list[str],
) -> dict[str, PerfilIG]:
    """Dado uma lista de handles, devolve dict handle -> PerfilIG.

    Handle nao retornado pela Apify simplesmente nao aparece no dict
    (o pipeline trata isso como "metricas indisponiveis").

    Engajamento aqui e REAL (likes+comentarios / seguidores), nao
    estimado por faixa.
    """
    if not handles:
        return {}

    # Normaliza handles (remove @, minusculo, dedup)
    handles_norm = list({h.lstrip("@").lower() for h in handles if h})
    if not handles_norm:
        return {}

    try:
        items = client.buscar_perfis_ig(handles_norm)
    except ApifyError as exc:
        logger.warning("Apify IG falhou: %s", exc)
        return {}

    perfis: dict[str, PerfilIG] = {}
    for raw in items:
        try:
            perfil = _parse_perfil_apify(raw)
            if perfil.handle:
                perfis[perfil.handle] = perfil
        except Exception as exc:
            logger.debug("Falha parseando perfil Apify: %s", exc)

    logger.info(
        "Apify IG: solicitados %d handles, recebidos %d perfis com metricas",
        len(handles_norm), len(perfis)
    )
    return perfis
