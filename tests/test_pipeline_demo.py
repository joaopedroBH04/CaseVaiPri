"""Teste end-to-end do pipeline em modo demo (sem rede).

Garante que as 3 especialidades cobertas em fixtures geram saida valida.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from vaipri_ref.config import Config
from vaipri_ref.pipeline import buscar_referencias


@pytest.fixture
def cfg_tmp():
    """Config com cache temporario e sem chave API."""
    with tempfile.TemporaryDirectory() as td:
        yield Config(
            anthropic_api_key=None,
            claude_model="claude-haiku-4-5-20251001",
            country="BR",
            max_candidatos=40,
            top_n=10,
            cache_dir=Path(td) / "cache",
            headless=True,
            verbose=False,
        )


@pytest.mark.parametrize("especialidade", ["dermatologia", "nutrologia", "ortopedia"])
def test_demo_gera_referencias_validas(cfg_tmp, especialidade):
    res = buscar_referencias(
        handle_cliente="@clinica.teste",
        especialidade=especialidade,
        config=cfg_tmp,
        modo_demo=True,
    )

    # Tem que devolver pelo menos algumas referencias (a fixture tem >= 10 validas)
    assert len(res.referencias) >= 5, f"Esperava >= 5 referencias, recebeu {len(res.referencias)}"
    assert len(res.referencias) <= 10

    # Avisos devem mencionar modo demo
    avisos_lower = " ".join(res.avisos).lower()
    assert "demo" in avisos_lower

    for ref in res.referencias:
        assert ref.confirmacao_anuncio_ativo is True
        assert ref.n_anuncios_ativos >= 1
        assert ref.especialidade_match is True
        assert 0.0 <= ref.especialidade_confianca <= 1.0
        assert 0.0 <= ref.score <= 100.0
        # contrato: campos obrigatorios estao preenchidos
        assert ref.instagram_handle
        assert str(ref.biblioteca_anuncios_url).startswith("https://www.facebook.com/ads/library/")
        assert ref.fb_page_id


def test_demo_ordena_por_score(cfg_tmp):
    res = buscar_referencias(
        "@x.cliente", "dermatologia", config=cfg_tmp, modo_demo=True
    )
    scores = [r.score for r in res.referencias]
    assert scores == sorted(scores, reverse=True)


def test_demo_filtra_especialidade_errada(cfg_tmp):
    """Na fixture de dermatologia existe um cardio e um plastica. Devem ser filtrados."""
    res = buscar_referencias(
        "@x.cliente", "dermatologia", config=cfg_tmp, modo_demo=True
    )
    # nenhum handle de cardio ou plastica deve aparecer
    handles = {r.instagram_handle for r in res.referencias}
    assert "dr.caiomarcos" not in handles  # cardio
    assert "dr.joaobrasil" not in handles  # plastica


def test_demo_exclui_proprio_cliente(cfg_tmp):
    """Se o handle do cliente bate com um da fixture, deve ser excluido."""
    res = buscar_referencias(
        "@draanalima.derm",  # esta na fixture de dermatologia
        "dermatologia",
        config=cfg_tmp,
        modo_demo=True,
    )
    handles = {r.instagram_handle for r in res.referencias}
    assert "draanalima.derm" not in handles


def test_input_invalido_handle_levanta_erro(cfg_tmp):
    with pytest.raises(ValueError):
        buscar_referencias("@@@", "dermatologia", config=cfg_tmp, modo_demo=True)


def test_especialidade_sem_fixture_emite_aviso(cfg_tmp):
    res = buscar_referencias(
        "@x.cliente", "geriatria", config=cfg_tmp, modo_demo=True
    )
    assert any("fixture" in a.lower() for a in res.avisos)
    assert res.referencias == []
