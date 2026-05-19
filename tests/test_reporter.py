"""Testes do reporter: serializacao para JSON, Markdown e HTML."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vaipri_ref.models import Metricas, Referencia, Resultado
from vaipri_ref.reporter import gerar_html, gerar_markdown, salvar


def _resultado_exemplo() -> Resultado:
    m = Metricas(
        seguidores=120_000,
        seguindo=420,
        total_posts=812,
        engajamento_estimado_percent=1.5,
        bio="Dermatologista CRM 12345",
        nome_completo="Dra. Teste",
        metricas_completas=True,
    )
    ref = Referencia(
        instagram_handle="dra.teste",
        instagram_url="https://www.instagram.com/dra.teste/",
        nome_exibicao="Dra. Teste",
        fb_page_id="111",
        fb_page_name="Dra. Teste Page",
        n_anuncios_ativos=10,
        biblioteca_anuncios_url="https://www.facebook.com/ads/library/?view_all_page_id=111",
        confirmacao_anuncio_ativo=True,
        metricas=m,
        especialidade_alvo="dermatologia",
        especialidade_match=True,
        especialidade_confianca=0.95,
        especialidade_justificativa="Bio menciona dermatologia.",
        score=8.5,
        score_breakdown={"Volume de anúncios rodando": 2.5, "Tração no Instagram": 1.2},
        score_rotulo="Excelente",
        confianca_handle="alta",
        notas=[],
    )
    return Resultado(
        handle_cliente="cliente",
        especialidade="dermatologia",
        pais="BR",
        gerado_em=datetime.now(timezone.utc),
        referencias=[ref],
        n_candidatos_brutos=20,
        n_filtrados_por_especialidade=5,
        n_descartados_sem_anuncio=2,
        termos_busca_usados=["dermatologista", "harmonizacao"],
    )


def test_gerar_markdown_contem_handle_e_score():
    res = _resultado_exemplo()
    md = gerar_markdown(res)
    assert "@dra.teste" in md
    assert "8.5/10" in md
    assert "dermatologia" in md.lower()


def test_gerar_html_renderiza_e_e_html_valido():
    res = _resultado_exemplo()
    html = gerar_html(res)
    assert "<!doctype html>" in html.lower()
    assert "@dra.teste" in html
    assert "8.5" in html
    # nao deve sair com tags Jinja nao renderizadas
    assert "{{" not in html
    assert "}}" not in html


def test_salvar_cria_3_arquivos():
    res = _resultado_exemplo()
    with tempfile.TemporaryDirectory() as td:
        paths = salvar(res, diretorio=td)
        assert paths["json"].exists()
        assert paths["md"].exists()
        assert paths["html"].exists()
        # JSON deve ser parseavel
        data = json.loads(paths["json"].read_text())
        assert data["handle_cliente"] == "cliente"
        assert data["referencias"][0]["instagram_handle"] == "dra.teste"


def test_resultado_vazio_nao_quebra():
    res = Resultado(
        handle_cliente="cliente",
        especialidade="raridade",
        pais="BR",
        gerado_em=datetime.now(timezone.utc),
        referencias=[],
        lista_incompleta=True,
        justificativa_lista_incompleta="Nada encontrado.",
    )
    md = gerar_markdown(res)
    html = gerar_html(res)
    assert "Nenhuma referencia" in md or "nenhuma" in md.lower()
    assert "Nenhuma" in html or "nenhuma" in html.lower()
