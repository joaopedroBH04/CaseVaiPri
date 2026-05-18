"""Testes do normalize: validacao basica de entrada do usuario."""

from __future__ import annotations

import pytest

from vaipri_ref.utils.normalize import (
    limpar_handle,
    slug,
    url_biblioteca_anuncios,
    url_busca_biblioteca,
    url_perfil_ig,
)


class TestLimparHandle:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("@dra.fulana", "dra.fulana"),
            ("dra.fulana", "dra.fulana"),
            ("@DRA.FULANA", "dra.fulana"),
            ("https://instagram.com/dra.fulana/", "dra.fulana"),
            ("https://www.instagram.com/dra.fulana", "dra.fulana"),
            ("  @dra.fulana  ", "dra.fulana"),
            ("dr_pedro_123", "dr_pedro_123"),
            ("a.b.c", "a.b.c"),
        ],
    )
    def test_aceita_variantes(self, entrada, esperado):
        assert limpar_handle(entrada) == esperado

    @pytest.mark.parametrize("entrada", ["", "  ", "@@", "user@host", "a b c", "x" * 31])
    def test_rejeita_invalidos(self, entrada):
        with pytest.raises(ValueError):
            limpar_handle(entrada)


class TestURLs:
    def test_perfil_ig(self):
        assert url_perfil_ig("@dra.fulana") == "https://www.instagram.com/dra.fulana/"

    def test_biblioteca_anuncios(self):
        url = url_biblioteca_anuncios("12345", "BR")
        assert "view_all_page_id=12345" in url
        assert "country=BR" in url
        assert "active_status=active" in url

    def test_busca_biblioteca(self):
        url = url_busca_biblioteca("dermatologista", "BR")
        assert "q=dermatologista" in url
        assert "search_type=keyword_unordered" in url


class TestSlug:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("Dermatologia", "dermatologia"),
            ("Cirurgia Plastica", "cirurgia-plastica"),
            ("Otorrinolaringologia", "otorrinolaringologia"),
            ("@clinica.exemplo", "clinica-exemplo"),
        ],
    )
    def test_slug_basico(self, entrada, esperado):
        assert slug(entrada) == esperado

    def test_slug_vazio(self):
        assert slug("") == "saida"
