"""Testes do parser de perfil IG e parser numerico."""

from __future__ import annotations

import pytest

from vaipri_ref.instagram.scraper import _parse_numero, _parse_perfil, estimar_engajamento


class TestParseNumero:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("12,5 mil", 12_500),
            ("1.2K", 1_200),
            ("1,2K", 1_200),
            ("1,234", 1_234),
            ("500", 500),
            ("2.5M", 2_500_000),
            ("2,5M", 2_500_000),
            ("1.000.000", 1_000_000),
            ("150K", 150_000),
            ("12.345", 12_345),
            ("", None),
            ("abc", None),
        ],
    )
    def test_casos(self, entrada, esperado):
        assert _parse_numero(entrada) == esperado


class TestParsePerfil:
    def test_pt_br(self):
        html = """<html><head>
<meta property="og:title" content="Dra. Fulana | Dermatologista (@dra.fulana) | Instagram" />
<meta property="og:description" content="48,5 mil Seguidores, 412 Seguindo, 1.234 Posts - Veja fotos do Instagram." />
</head></html>"""
        p = _parse_perfil(html, "dra.fulana", "https://www.instagram.com/dra.fulana/")
        assert p.seguidores == 48_500
        assert p.seguindo == 412
        assert p.total_posts == 1_234
        assert "Dermatologista" in (p.nome_completo or "")
        assert p.metricas_completas

    def test_en(self):
        html = """<html><head>
<meta property="og:title" content="Dr. X (@dr.x)" />
<meta property="og:description" content="12.5K Followers, 200 Following, 567 Posts - See..." />
</head></html>"""
        p = _parse_perfil(html, "dr.x", "https://www.instagram.com/dr.x/")
        assert p.seguidores == 12_500
        assert p.total_posts == 567

    def test_sem_og(self):
        html = "<html><body>nothing</body></html>"
        p = _parse_perfil(html, "ghost", "https://www.instagram.com/ghost/")
        assert p.seguidores is None
        assert not p.metricas_completas


class TestEstimarEngajamento:
    @pytest.mark.parametrize(
        "n,esperado",
        [
            (None, None),
            (0, None),
            (1_000, 4.0),
            (10_000, 2.5),
            (50_000, 1.5),
            (250_000, 0.9),
            (1_500_000, 0.6),
        ],
    )
    def test_faixas(self, n, esperado):
        assert estimar_engajamento(n) == esperado
