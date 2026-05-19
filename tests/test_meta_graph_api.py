"""Testes do adapter Meta Graph API.

Sem fazer chamadas reais à internet — usamos httpx mock pra
validar o contrato e a serializacao.
"""

from __future__ import annotations

import json

import httpx
import pytest

from vaipri_ref.discovery.meta_graph_api import (
    AnuncioGraph,
    GraphAPIError,
    MetaGraphAPI,
    _parse_anuncio,
)


# =================================================================
# Construcao e validacao basica
# =================================================================


class TestConstrucao:
    def test_requer_access_token(self):
        with pytest.raises(ValueError, match="access_token"):
            MetaGraphAPI(access_token="")

    def test_disponivel_com_token(self):
        api = MetaGraphAPI(access_token="fake-token-123")
        assert api.disponivel is True

    def test_country_default_br(self):
        api = MetaGraphAPI(access_token="x")
        assert api.country == "BR"


# =================================================================
# Parsing de anuncios brutos
# =================================================================


class TestParseAnuncio:
    def test_anuncio_completo(self):
        raw = {
            "id": "12345",
            "page_id": "67890",
            "page_name": "Dra. Fulana",
            "ad_creation_time": "2024-09-01T00:00:00+0000",
            "ad_delivery_start_time": "2024-09-15T00:00:00+0000",
            "ad_snapshot_url": "https://www.facebook.com/ads/library/?id=12345",
            "publisher_platforms": ["facebook", "instagram"],
        }
        a = _parse_anuncio(raw)
        assert a.ad_id == "12345"
        assert a.page_id == "67890"
        assert a.page_name == "Dra. Fulana"
        assert a.ativo is True  # sem ad_delivery_stop_time = ativo
        assert "instagram" in (a.plataformas or [])

    def test_anuncio_inativo(self):
        raw = {
            "id": "1",
            "page_id": "2",
            "page_name": "X",
            "ad_delivery_stop_time": "2024-10-01T00:00:00+0000",
        }
        a = _parse_anuncio(raw)
        assert a.ativo is False
        assert a.fim is not None

    def test_anuncio_minimo(self):
        raw = {"id": "1", "page_id": "2", "page_name": "Z"}
        a = _parse_anuncio(raw)
        assert a.ad_id == "1"
        assert a.ativo is True


# =================================================================
# Agrupamento por pagina (logica core)
# =================================================================


class TestAgrupamento:
    def test_agrupa_por_page_id(self):
        api = MetaGraphAPI(access_token="x")
        anuncios = [
            AnuncioGraph(ad_id="1", page_id="100", page_name="Dr. A"),
            AnuncioGraph(ad_id="2", page_id="100", page_name="Dr. A"),
            AnuncioGraph(ad_id="3", page_id="200", page_name="Dr. B"),
        ]
        out = api.agrupar_por_pagina(anuncios)
        out_map = {pid: (nome, n) for pid, nome, n in out}
        assert out_map["100"] == ("Dr. A", 2)
        assert out_map["200"] == ("Dr. B", 1)

    def test_lista_vazia(self):
        api = MetaGraphAPI(access_token="x")
        assert api.agrupar_por_pagina([]) == []


# =================================================================
# Tratamento de erros HTTP da Graph API
# =================================================================


class TestErrosGraph:
    def test_401_levanta_graph_api_error(self, monkeypatch):
        """401 deve virar GraphAPIError com mensagem util."""
        def mock_get(self, url, params=None):
            req = httpx.Request("GET", url)
            return httpx.Response(
                401,
                json={"error": {"message": "Invalid OAuth access token", "code": 190}},
                request=req,
            )

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        api = MetaGraphAPI(access_token="invalido")
        with pytest.raises(GraphAPIError) as exc:
            api.buscar_termo("dermatologista", limite=10)
        assert exc.value.status_code == 401
        assert "Acesso negado" in str(exc.value)

    def test_400_levanta_graph_api_error(self, monkeypatch):
        def mock_get(self, url, params=None):
            req = httpx.Request("GET", url)
            return httpx.Response(
                400,
                json={"error": {"message": "Missing required parameter"}},
                request=req,
            )

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        api = MetaGraphAPI(access_token="x")
        with pytest.raises(GraphAPIError) as exc:
            api.buscar_termo("x", limite=10)
        assert exc.value.status_code == 400


# =================================================================
# Sucesso: parsing de resposta da Meta
# =================================================================


class TestSucesso:
    def test_resposta_normal(self, monkeypatch):
        """Resposta tipica da Graph API: lista de anuncios em data[]"""
        resp_body = {
            "data": [
                {
                    "id": "100100100100",
                    "page_id": "200200200200",
                    "page_name": "Dra. Ana Lima Dermatologia",
                    "ad_creation_time": "2024-09-15T10:00:00+0000",
                    "ad_snapshot_url": "https://www.facebook.com/ads/library/?id=100100100100",
                },
                {
                    "id": "100100100101",
                    "page_id": "200200200200",
                    "page_name": "Dra. Ana Lima Dermatologia",
                    "ad_creation_time": "2024-09-16T10:00:00+0000",
                },
                {
                    "id": "100100100102",
                    "page_id": "300300300300",
                    "page_name": "Clinica Pele Boa",
                    "ad_creation_time": "2024-10-01T10:00:00+0000",
                },
            ]
        }

        def mock_get(self, url, params=None):
            req = httpx.Request("GET", url)
            return httpx.Response(200, json=resp_body, request=req)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        api = MetaGraphAPI(access_token="x")
        anuncios = api.buscar_termo("dermatologista", limite=50)
        assert len(anuncios) == 3
        agrupado = {pid: (nome, n) for pid, nome, n in api.agrupar_por_pagina(anuncios)}
        assert agrupado["200200200200"][1] == 2  # 2 anuncios da mesma pagina
        assert agrupado["300300300300"][1] == 1

    def test_resposta_vazia(self, monkeypatch):
        def mock_get(self, url, params=None):
            req = httpx.Request("GET", url)
            return httpx.Response(200, json={"data": []}, request=req)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        api = MetaGraphAPI(access_token="x")
        assert api.buscar_termo("inexistente", limite=10) == []


# =================================================================
# Integracao: scraper detecta token e usa Graph API
# =================================================================


class TestIntegracaoComScraper:
    def test_scraper_sem_token_usa_caminho_legado(self):
        from vaipri_ref.discovery.meta_ad_library import MetaAdLibraryScraper
        from vaipri_ref.utils.cache import Cache
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            cache = Cache(Path(td))
            try:
                s = MetaAdLibraryScraper(cache=cache, graph_api_token=None)
                assert s.usando_graph_api is False
            finally:
                cache.close()

    def test_scraper_com_token_usa_graph(self):
        from vaipri_ref.discovery.meta_ad_library import MetaAdLibraryScraper
        from vaipri_ref.utils.cache import Cache
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            cache = Cache(Path(td))
            try:
                s = MetaAdLibraryScraper(cache=cache, graph_api_token="EAAxxxxxxxx")
                assert s.usando_graph_api is True
            finally:
                cache.close()
