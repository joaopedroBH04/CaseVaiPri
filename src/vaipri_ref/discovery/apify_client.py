"""Cliente HTTP para a Apify Platform.

Por que Apify e nao Graph API: a Graph API oficial da Meta exige
App Review (processo de dias) para usar ads_archive em produção,
e o Instagram bloqueia scraping anonimo desde 2022. Apify ja tem
actors prontos e robustos que cobrem ambos os casos:

- `apify/facebook-ads-library-scraper`: busca anuncios na Ad Library
  com nomes REAIS de paginas, instagram handle quando disponivel,
  links pra cada anuncio, etc.

- `apify/instagram-profile-scraper`: dado um handle, retorna
  seguidores, engajamento real (likes+comentarios dos ultimos posts),
  bio, foto, posts recentes.

Usamos a Apify API via HTTP (nao o SDK Python deles) para manter
as dependencias controladas. Endpoint `run-sync-get-dataset-items`
roda o actor e devolve resultados em uma so chamada (sincrona).

Custos tipicos por busca (com $5 grátis do free tier):
- Ad Library: ~$0.02-0.05 por keyword
- Instagram: ~$0.02-0.05 por perfil
- 1 busca completa (10 keywords + 10 perfis) ≈ $0.40-0.70.
- $5 ≈ 7-12 buscas completas. Mais que suficiente pra avaliacao.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from vaipri_ref.utils.logger import obter as obter_logger


logger = obter_logger()


# Actors padrao. O usuario pode trocar via env se quiser outro provider.
_DEFAULT_AD_LIBRARY_ACTOR = "curious_coder~facebook-ads-library-scraper"
_DEFAULT_IG_ACTOR = "apify~instagram-profile-scraper"

_API_BASE = "https://api.apify.com/v2"


class ApifyError(Exception):
    """Erro especifico do cliente Apify."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass
class _ApifyConfig:
    api_token: str
    ad_library_actor: str = _DEFAULT_AD_LIBRARY_ACTOR
    ig_actor: str = _DEFAULT_IG_ACTOR
    timeout_total: float = 180.0  # actors podem demorar


class ApifyClient:
    """Wrapper leve para a Apify Platform.

    Sem dependencia do SDK oficial — usamos httpx direto.
    """

    def __init__(
        self,
        api_token: str,
        *,
        ad_library_actor: str = _DEFAULT_AD_LIBRARY_ACTOR,
        ig_actor: str = _DEFAULT_IG_ACTOR,
        timeout_total: float = 180.0,
    ) -> None:
        if not api_token or len(api_token.strip()) < 20:
            raise ValueError(
                "Token Apify invalido (vazio ou muito curto). "
                "Pegue em apify.com > Settings > Integrations > API tokens."
            )
        api_token = api_token.strip()
        if not api_token.startswith("apify_api_"):
            logger.warning(
                "Token Apify nao comeca com 'apify_api_'. Vou tentar mesmo assim, "
                "mas confira em apify.com > Settings > Integrations se o token esta correto."
            )
        self._cfg = _ApifyConfig(
            api_token=api_token,
            ad_library_actor=ad_library_actor,
            ig_actor=ig_actor,
            timeout_total=timeout_total,
        )

    @property
    def disponivel(self) -> bool:
        return bool(self._cfg.api_token)

    # ===========================================================
    # Ad Library — busca anuncios reais com nomes e handle IG
    # ===========================================================

    def buscar_ad_library(
        self,
        termo: str,
        *,
        country: str = "BR",
        max_resultados: int = 50,
        somente_ativos: bool = True,
    ) -> list[dict[str, Any]]:
        """Roda actor de Ad Library para um termo de busca.

        Retorna lista de dicts brutos (formato definido pelo actor).
        Os campos esperados (variam por actor) incluem:
          - pageId / page_id          : ID FB da pagina
          - pageName / page_name      : nome publico
          - adArchiveId / ad_archive_id
          - snapshotUrl / snapshot_url
          - linkUrl                   : URL externa do anuncio
          - igUsername / ig_username  : handle IG quando disponivel
          - startDate / endDate
        """
        # URL publica da Ad Library (mesmo padrao da UI):
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status={'active' if somente_ativos else 'all'}"
            f"&ad_type=all&country={country}&q={termo}"
            f"&search_type=keyword_unordered&media_type=all"
        )

        run_input = {
            "urls": [{"url": url}],
            "count": max_resultados,
            "scrapeAdDetails": True,
            "scrapePageAds.activeStatus": "active" if somente_ativos else "all",
            "period": "30",
        }
        try:
            items = self._run_sync(self._cfg.ad_library_actor, run_input)
            return items[:max_resultados]
        except ApifyError as exc:
            logger.warning("Apify Ad Library falhou em %r: %s", termo, exc)
            raise

    # ===========================================================
    # Instagram — pega seguidores, engajamento REAL, bio, posts
    # ===========================================================

    def buscar_perfis_ig(self, handles: list[str]) -> list[dict[str, Any]]:
        """Roda actor de Instagram para uma lista de handles.

        Retorna lista de dicts brutos. Campos comuns:
          - username                 : @ sem o @
          - fullName                 : nome completo no IG
          - biography                : bio
          - followersCount           : seguidores
          - followsCount             : seguindo
          - postsCount               : total de posts
          - profilePicUrl            : foto de perfil
          - verified                 : bool selo azul
          - latestPosts              : lista com curtidas/comentarios dos ultimos
        """
        if not handles:
            return []

        run_input = {
            "usernames": handles,
            "resultsType": "details",
            "resultsLimit": 1,
        }
        try:
            items = self._run_sync(self._cfg.ig_actor, run_input)
            return items
        except ApifyError as exc:
            logger.warning("Apify IG falhou para %d perfis: %s", len(handles), exc)
            raise

    # ===========================================================
    # Validacao do token (1 chamada minima)
    # ===========================================================

    def validar_token(self) -> tuple[bool, str]:
        """Bate em /users/me. Retorna (ok, mensagem)."""
        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.get(
                    f"{_API_BASE}/users/me",
                    params={"token": self._cfg.api_token},
                )
            if r.status_code == 200:
                data = r.json().get("data", {})
                username = data.get("username", "?")
                return True, f"Token aceito pela Apify (conta: {username})."
            return False, f"Apify rejeitou o token (HTTP {r.status_code}): {r.text[:200]}"
        except Exception as exc:
            return False, f"Falha ao validar token Apify: {exc}"

    # ===========================================================
    # Internal: run actor synchronously
    # ===========================================================

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _run_sync(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        """Roda actor e devolve os dataset items.

        Usa o endpoint `run-sync-get-dataset-items` da Apify: posta o
        input, espera o actor terminar (com timeout do servidor), e
        recebe os items de volta direto no body.
        """
        url = f"{_API_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
        params = {"token": self._cfg.api_token, "format": "json"}

        try:
            with httpx.Client(timeout=self._cfg.timeout_total) as c:
                r = c.post(url, params=params, json=run_input)
        except httpx.TimeoutException as exc:
            raise ApifyError(f"Timeout esperando actor {actor_id}: {exc}") from exc
        except Exception as exc:
            raise ApifyError(f"Erro de rede: {exc}") from exc

        if r.status_code == 404:
            raise ApifyError(
                f"Actor {actor_id!r} nao encontrado. Verifique o nome ou troque "
                "via env (APIFY_AD_LIBRARY_ACTOR / APIFY_IG_ACTOR).",
                status_code=404,
            )
        if r.status_code in (401, 403):
            raise ApifyError(
                f"Apify rejeitou o token (HTTP {r.status_code}). "
                "Verifique APIFY_API_TOKEN no .env.",
                status_code=r.status_code,
            )
        if r.status_code == 402:
            raise ApifyError(
                "Apify retornou 402 (Payment Required). Voce esgotou o credito "
                "gratuito ($5 inicial). Adicione metodo de pagamento ou rode --demo.",
                status_code=402,
            )
        if r.status_code >= 500:
            raise ApifyError(
                f"Erro do servidor Apify: {r.status_code} {r.text[:200]}",
                status_code=r.status_code,
            )
        if r.status_code != 200 and r.status_code != 201:
            raise ApifyError(
                f"Apify HTTP {r.status_code}: {r.text[:300]}",
                status_code=r.status_code,
            )

        try:
            data = r.json()
        except Exception as exc:
            raise ApifyError(f"Resposta nao-JSON da Apify: {r.text[:200]}") from exc

        if not isinstance(data, list):
            # API as vezes devolve dict de erro
            if isinstance(data, dict) and "error" in data:
                raise ApifyError(
                    f"Apify retornou erro: {data.get('error', {}).get('message', data)}",
                    body=data,
                )
            raise ApifyError(f"Resposta inesperada da Apify (esperava list): {type(data)}")

        return data
