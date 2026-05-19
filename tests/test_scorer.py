"""Testes do scorer: a formula precisa ser determinista e respeitar limites.

A escala oficial e 0-10 (com nomes humanos no breakdown), nao 0-100.
"""

from __future__ import annotations

import pytest

from vaipri_ref.scorer import EntradaScore, calcular, rotulo_qualitativo


def _entrada(**kw):
    base = dict(
        n_anuncios_ativos=5,
        seguidores=20_000,
        engajamento_percent=1.5,
        bio_menciona_especialidade=True,
        posts_ultimos_30_dias=3,
        confianca_handle="alta",
    )
    base.update(kw)
    return EntradaScore(**base)


def test_score_dentro_de_0_a_10():
    score, _ = calcular(_entrada())
    assert 0 <= score <= 10


def test_volume_de_ads_pesa_mais_que_seguidores():
    # mantendo tudo igual, mais ads deve aumentar score mais do que +seguidores
    s_baseline, _ = calcular(_entrada(n_anuncios_ativos=5, seguidores=20_000))
    s_mais_ads, _ = calcular(_entrada(n_anuncios_ativos=15, seguidores=20_000))
    s_mais_seg, _ = calcular(_entrada(n_anuncios_ativos=5, seguidores=80_000))

    assert s_mais_ads > s_baseline
    assert s_mais_seg > s_baseline
    # +10 ads vale mais que +60k seguidores
    assert (s_mais_ads - s_baseline) > (s_mais_seg - s_baseline)


def test_score_zero_no_pior_caso_possivel():
    score, _ = calcular(
        _entrada(
            n_anuncios_ativos=0,
            seguidores=None,
            engajamento_percent=None,
            bio_menciona_especialidade=False,
            posts_ultimos_30_dias=0,
            confianca_handle="baixa",
        )
    )
    # com handle baixo soma 0.2; resto zera
    assert score <= 0.5


def test_score_alto_no_melhor_caso():
    score, _ = calcular(
        _entrada(
            n_anuncios_ativos=50,
            seguidores=300_000,
            engajamento_percent=2.0,
            bio_menciona_especialidade=True,
            posts_ultimos_30_dias=10,
            confianca_handle="alta",
        )
    )
    assert score >= 9.5


@pytest.mark.parametrize("confianca,esperado", [("alta", 1.0), ("media", 0.6), ("baixa", 0.2)])
def test_handle_confianca_peso(confianca, esperado):
    _, bd = calcular(_entrada(confianca_handle=confianca))
    assert bd["Confiabilidade do match"] == esperado


def test_breakdown_soma_igual_total():
    score, bd = calcular(_entrada())
    assert abs(sum(bd.values()) - score) < 0.01


def test_seguidores_none_zera_parcela():
    _, bd = calcular(_entrada(seguidores=None))
    assert bd["Tração no Instagram"] == 0.0


def test_postagem_recente_none_credito_parcial():
    """Sem dado, damos credito parcial (nao zero) para nao penalizar IG bloqueado."""
    _, bd = calcular(_entrada(posts_ultimos_30_dias=None))
    assert 0 < bd["Perfil ativo (posts recentes)"] < 1.5


def test_rotulos_qualitativos():
    """Nota -> rotulo humano."""
    assert rotulo_qualitativo(9.0) == "Excelente"
    assert rotulo_qualitativo(7.5) == "Muito boa"
    assert rotulo_qualitativo(6.0) == "Boa"
    assert rotulo_qualitativo(4.5) == "Razoável"
    assert rotulo_qualitativo(2.0) == "Fraca"


def test_chaves_do_breakdown_sao_em_portugues():
    """Garante que o breakdown usa nomes humanos."""
    _, bd = calcular(_entrada())
    chaves_esperadas = {
        "Volume de anúncios rodando",
        "Tração no Instagram",
        "Engajamento real",
        "Perfil ativo (posts recentes)",
        "Identidade médica clara",
        "Confiabilidade do match",
    }
    assert set(bd.keys()) == chaves_esperadas
