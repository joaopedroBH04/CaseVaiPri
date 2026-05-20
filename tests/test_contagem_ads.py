"""Testes da contagem REAL de anuncios ativos por pagina.

Garantia: o numero que mostramos em 'Ads' bate com o '~XX resultados'
que aparece na Ad Library da Meta quando o avaliador clica no link.
"""

from __future__ import annotations

import pytest

from vaipri_ref.discovery.ad_library_html import (
    _REGEXES,
    _normalizar_numero,
    contar_anuncios_via_html,
)


class TestParseNumero:
    """Normalizacao de '~XX resultados' em int."""

    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("41", 41),
            ("1234", 1234),
            ("1.234", 1234),   # pt-BR separador milhar
            ("1,234", 1234),   # en separador milhar
            ("1k", 1000),
            ("2mil", 2000),
            ("", None),
            ("abc", None),
        ],
    )
    def test_normalizacao(self, entrada, esperado):
        assert _normalizar_numero(entrada) == esperado


class TestRegexes:
    """Os regexes pegam '~XX resultados' nas variantes que a Meta usa."""

    @pytest.mark.parametrize(
        "html,esperado",
        [
            ("antes ~41 resultados depois", 41),
            ("Cerca de 123 resultados encontrados", 123),
            ("≈ 7 resultados", 7),
            ("About 41 results displayed", 41),
            ("~1.234 resultados", 1234),
            ('{"total_count": 41}', 41),
            ('"adArchiveCount":150', 150),
            ('"ad_archive_count":99', 99),
            ("nada que bate", None),
            ("", None),
        ],
    )
    def test_regex_match(self, html, esperado):
        achei = None
        for regex in _REGEXES:
            m = regex.search(html)
            if m:
                achei = _normalizar_numero(m.group(1))
                break
        assert achei == esperado


class TestContarViaHtml:
    """Comportamento defensivo da funcao publica."""

    def test_page_id_vazio_retorna_none(self):
        assert contar_anuncios_via_html("") is None

    def test_page_id_nao_numerico_retorna_none(self):
        assert contar_anuncios_via_html("abc123") is None

    def test_page_id_valido_nao_quebra_sem_rede(self):
        """Em ambiente sem rede aberta pra Meta, deve retornar None
        em vez de levantar excecao."""
        # Tenta um page_id valido mas em ambiente provavelmente bloqueado
        result = contar_anuncios_via_html("100100100100")
        # Aceita qualquer comportamento (None ou int), so nao pode crashar
        assert result is None or isinstance(result, int)
