"""Adapter para a Meta Ad Library Graph API oficial.

Endpoint: https://graph.facebook.com/v19.0/ads_archive

Por que este caminho:
- E o caminho OFICIAL e ESTAVEL da Meta para buscar anuncios na
  Biblioteca de Anuncios.
- Funciona em QUALQUER rede (nao depende do IP nao ser bloqueado).
- Retorna dados estruturados em JSON.
- Gratuito (com Facebook Developer Account, tambem gratuita).

Como conseguir o token: ver docs/COMO_ATIVAR_DADOS_REAIS.md.

Limitacoes documentadas pela Meta:
- ad_type=ALL cobre todos os anuncios (incluindo medicos).
- Para alguns campos avancados, a app precisa de review da Meta.
  Nos usamos apenas os campos basicos, que nao requerem review.
- Rate limit de ~200 chamadas/hora por app — suficiente pra demo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from vaipri_ref.utils.logger import obter as obter_logger


logger = obter_logger()

# Campos basicos que NAO requerem app review da Meta.
# https://developers.facebook.com/docs/graph-api/reference/ads_archive/
_CAMPOS_BASE = ",".join([
    "id",
    "page_id",
    "page_name",
    "ad_creation_time",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "ad_snapshot_url",
    "publisher_platforms",
])

_GRAPH_VERSION = "v19.0"
_BASE_URL = f"https://graph.facebook.com/{_GRAPH_VERSION}/ads_archive"


@dataclass
class AnuncioGraph:
    """Representacao de um anuncio retornado pela Graph API."""

    ad_id: str
    page_id: str
    page_name: str
    snapshot_url: str | None = None
    inicio: str | None = None  # ISO timestamp
    fim: str | None = None     # ISO timestamp (ou None se ativo)
    ativo: bool = True
    plataformas: list[str] | None = None


class GraphAPIError(Exception):
    """Erro especifico da Graph API. Usado pra distinguir de falhas de rede."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class MetaGraphAPI:
    """Cliente para a Ad Library via Graph API oficial."""

    def __init__(
        self,
        access_token: str,
        country: str = "BR",
        timeout: float = 30.0,
        page_size: int = 50,
    ) -> None:
        if not access_token:
            raise ValueError("access_token obrigatorio para usar a Graph API.")
        self.access_token = access_token
        self.country = country
        self.timeout = timeout
        self.page_size = page_size

    @property
    def disponivel(self) -> bool:
        return bool(self.access_token)

    def buscar_termo(
        self,
        termo: str,
        *,
        limite: int = 50,
        somente_ativos: bool = True,
    ) -> list[AnuncioGraph]:
        """Busca anuncios para um termo (keyword) na Biblioteca."""
        params: dict[str, Any] = {
            "search_terms": termo,
            "ad_reached_countries": json.dumps([self.country]),
            "ad_type": "ALL",
            "fields": _CAMPOS_BASE,
            "access_token": self.access_token,
            "limit": min(self.page_size, limite),
        }
        if somente_ativos:
            params["ad_active_status"] = "ACTIVE"

        anuncios: list[AnuncioGraph] = []
        url = _BASE_URL
        try:
            while len(anuncios) < limite:
                data = self._chamar(url, params if url == _BASE_URL else None)
                for raw in data.get("data", []):
                    anuncios.append(_parse_anuncio(raw))
                    if len(anuncios) >= limite:
                        break
                # paginacao
                proxima = data.get("paging", {}).get("next")
                if not proxima:
                    break
                url = proxima
                params = None  # ja embutidos na URL next
        except GraphAPIError as exc:
            logger.warning("Graph API falhou em '%s': %s", termo, exc)
            raise

        return anuncios

    def agrupar_por_pagina(
        self,
        anuncios: list[AnuncioGraph],
    ) -> list[tuple[str, str, int]]:
        """Agrupa anuncios por page_id e devolve (page_id, page_name, n_anuncios)."""
        contagem: dict[str, tuple[str, int]] = {}
        for a in anuncios:
            if a.page_id in contagem:
                nome, n = contagem[a.page_id]
                contagem[a.page_id] = (nome, n + 1)
            else:
                contagem[a.page_id] = (a.page_name, 1)
        return [(pid, nome, n) for pid, (nome, n) in contagem.items()]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _chamar(self, url: str, params: dict[str, Any] | None) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(url, params=params)

        if r.status_code == 400:
            body = _parse_body(r)
            erro = body.get("error", {}) if isinstance(body, dict) else {}
            msg = erro.get("message", r.text[:200])
            raise GraphAPIError(f"Bad Request: {msg}", status_code=400, body=body)
        if r.status_code in (401, 403):
            body = _parse_body(r)
            erro = body.get("error", {}) if isinstance(body, dict) else {}
            msg = erro.get("message", "credencial invalida ou sem permissao")
            raise GraphAPIError(
                f"Acesso negado: {msg}. Verifique META_ACCESS_TOKEN no .env "
                "(ver docs/COMO_ATIVAR_DADOS_REAIS.md).",
                status_code=r.status_code,
                body=body,
            )
        if r.status_code == 429:
            raise GraphAPIError("Rate limit atingido (429).", status_code=429)
        if r.status_code >= 500:
            raise GraphAPIError(f"Erro do servidor Meta: {r.status_code}", status_code=r.status_code)

        r.raise_for_status()
        return r.json()


# ---------- helpers ----------


def _parse_body(r: httpx.Response) -> Any:
    try:
        return r.json()
    except Exception:
        return r.text


def _parse_anuncio(raw: dict[str, Any]) -> AnuncioGraph:
    inicio = raw.get("ad_delivery_start_time") or raw.get("ad_creation_time")
    fim = raw.get("ad_delivery_stop_time")
    ativo = fim is None  # se nao ha fim, esta veiculando
    return AnuncioGraph(
        ad_id=str(raw.get("id", "")),
        page_id=str(raw.get("page_id", "")),
        page_name=str(raw.get("page_name", "")),
        snapshot_url=raw.get("ad_snapshot_url"),
        inicio=inicio,
        fim=fim,
        ativo=ativo,
        plataformas=raw.get("publisher_platforms"),
    )


def validar_token(access_token: str) -> tuple[bool, str]:
    """Faz uma chamada minima para validar o token. Retorna (ok, mensagem).

    Util para CLI exibir feedback antes da busca pesada.
    """
    if not access_token:
        return False, "Token vazio."
    try:
        api = MetaGraphAPI(access_token=access_token)
        # Chamada minima: search_terms vazio + limit 1
        params: dict[str, Any] = {
            "search_terms": "saude",
            "ad_reached_countries": json.dumps(["BR"]),
            "ad_type": "ALL",
            "ad_active_status": "ACTIVE",
            "fields": "id",
            "access_token": access_token,
            "limit": 1,
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.get(_BASE_URL, params=params)
        if r.status_code == 200:
            return True, "Token aceito pela Meta Graph API."
        body = _parse_body(r)
        msg = ""
        if isinstance(body, dict):
            msg = body.get("error", {}).get("message", "")
        return False, f"Meta rejeitou o token (HTTP {r.status_code}): {msg}"
    except Exception as exc:
        return False, f"Falha ao validar token: {exc}"
