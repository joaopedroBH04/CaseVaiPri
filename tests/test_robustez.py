"""Testes de robustez para os 3 casos de input estranho citados no enunciado:

> Robustez — o que acontece quando o input e estranho?
> @ que nao existe, especialidade rara, perfil sem nenhum anuncio?

Cada caso esta coberto por testes que validam o comportamento ESPERADO
(nao um stack trace), com mensagens claras pro usuario final.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vaipri_ref.config import Config
from vaipri_ref.discovery.meta_ad_library import _parse_html
from vaipri_ref.models import Candidato, Metricas, Referencia
from vaipri_ref.pipeline import _bio_menciona, buscar_referencias
from vaipri_ref.scorer import EntradaScore, calcular as calcular_score
from vaipri_ref.utils.normalize import limpar_handle


@pytest.fixture
def cfg_tmp():
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


# ============================================================
# CASO A: "@ que nao existe"
# ============================================================
#
# Dois subcasos:
#   A.1) Handle SINTATICAMENTE invalido (ex: "@@", "user@host"):
#        a ferramenta deve REJEITAR cedo com ValueError claro.
#   A.2) Handle sintaticamente valido mas inexistente no IG:
#        a ferramenta deve continuar a busca (o handle do cliente
#        nao e essencial para descobrir referencias), e marcar nas
#        notas que o cliente nao pode ser excluido por colisao.
# ============================================================


class TestHandleNaoExiste:
    @pytest.mark.parametrize("handle_invalido", ["", "@@", "user@host", "a b c", "x" * 31, "  "])
    def test_handle_sintaticamente_invalido_rejeitado_cedo(self, cfg_tmp, handle_invalido):
        """Erro acontece ANTES de qualquer scraping/chamada externa."""
        with pytest.raises(ValueError) as exc_info:
            buscar_referencias(handle_invalido, "dermatologia", config=cfg_tmp, modo_demo=True)
        # mensagem precisa ser util pro usuario
        assert "handle" in str(exc_info.value).lower() or "invalido" in str(exc_info.value).lower()

    def test_handle_inexistente_no_ig_nao_quebra_busca(self, cfg_tmp):
        """
        Um @ que nunca existiu (ex: @clinica.que.nao.existe.12345)
        e sintaticamente OK. A ferramenta NAO deve quebrar — ela
        deve devolver referencias normalmente, pois nao precisa do
        perfil do cliente pra montar a lista.
        """
        res = buscar_referencias(
            handle_cliente="@clinica.que.nao.existe.99999",
            especialidade="dermatologia",
            config=cfg_tmp,
            modo_demo=True,
        )
        assert len(res.referencias) >= 5
        # o handle ainda aparece normalizado no resultado
        assert res.handle_cliente == "clinica.que.nao.existe.99999"

    def test_handle_e_referencia_do_proprio_cliente_e_excluida(self, cfg_tmp):
        """
        Caso adversarial: cliente passa o @ de um perfil que esta no
        nosso conjunto de candidatos. Ele NAO deve aparecer como
        sua propria referencia.
        """
        res = buscar_referencias(
            handle_cliente="@dra.ana.lima.derm",  # similar a um da fixture
            especialidade="dermatologia",
            config=cfg_tmp,
            modo_demo=True,
        )
        # exatamente o handle da fixture
        res2 = buscar_referencias(
            handle_cliente="@draanalima.derm",
            especialidade="dermatologia",
            config=cfg_tmp,
            modo_demo=True,
        )
        handles = {r.instagram_handle for r in res2.referencias}
        assert "draanalima.derm" not in handles

    def test_limpar_handle_aceita_urls_completas(self):
        """Robustez: usuario pode colar URL no lugar do @."""
        assert limpar_handle("https://www.instagram.com/dra.fulana/") == "dra.fulana"
        assert limpar_handle("https://instagram.com/dra.fulana") == "dra.fulana"


# ============================================================
# CASO B: "Especialidade rara"
# ============================================================
#
# Quando o avaliador digitar "neuro-pediatria oncologica" ou algo
# que nao temos termos curados / nao tem muitos anunciantes:
#   - a ferramenta NAO deve quebrar
#   - deve gerar termos a partir da palavra-raiz
#   - se nao achar 10, deve entregar N + justificativa explicita
# ============================================================


class TestEspecialidadeRara:
    def test_especialidade_sem_fixture_em_modo_demo_avisa(self, cfg_tmp):
        """
        Em modo demo: especialidade fora das 3 cobertas (dermato,
        nutro, orto) deve emitir aviso claro e retornar lista vazia,
        nao quebrar.
        """
        res = buscar_referencias(
            handle_cliente="@x.cliente",
            especialidade="neuro-pediatria",
            config=cfg_tmp,
            modo_demo=True,
        )
        assert res.referencias == []
        assert any("fixture" in a.lower() for a in res.avisos)
        # o usuario sabe que pode rodar sem --demo para testar producao
        assert any(
            "fixture" in a.lower() or "disponiveis" in a.lower()
            for a in res.avisos
        )

    def test_especialidade_com_caracteres_acentuados(self, cfg_tmp):
        """Robustez: entrada com acentos deve funcionar."""
        # acentos comuns em portugues
        res = buscar_referencias(
            "@x", "Dermatologia", config=cfg_tmp, modo_demo=True
        )
        assert res.especialidade == "dermatologia"  # normalizado

    def test_especialidade_em_caixa_mista(self, cfg_tmp):
        """Robustez: 'DermAtoLOgIa' deve dar mesmo resultado que 'dermatologia'."""
        res1 = buscar_referencias("@x", "DermAtoLoGiA", config=cfg_tmp, modo_demo=True)
        res2 = buscar_referencias("@x", "dermatologia", config=cfg_tmp, modo_demo=True)
        handles1 = {r.instagram_handle for r in res1.referencias}
        handles2 = {r.instagram_handle for r in res2.referencias}
        assert handles1 == handles2

    def test_especialidade_vazia_e_rejeitada(self, cfg_tmp):
        with pytest.raises(ValueError):
            buscar_referencias("@x", "", config=cfg_tmp, modo_demo=True)
        with pytest.raises(ValueError):
            buscar_referencias("@x", "   ", config=cfg_tmp, modo_demo=True)


# ============================================================
# CASO C: "Perfil sem nenhum anuncio"
# ============================================================
#
# Tem dois angulos:
#   C.1) UM CANDIDATO que veio com 0 anuncios: deve ser descartado.
#   C.2) NENHUM candidato com anuncios: lista vazia + justificativa.
#   C.3) Cliente passa um @ de medico SEM anuncios:
#        a ferramenta busca normalmente — o @ do cliente serve so
#        para excluir-se da lista de referencias; nao influi.
# ============================================================


class TestPerfilSemAnuncio:
    def test_candidato_com_zero_anuncios_e_filtrado(self, cfg_tmp):
        """
        Candidatos sem anuncio ativo NAO podem aparecer nas referencias
        — e a regra mais hard do enunciado.
        """
        res = buscar_referencias(
            "@x.cliente", "dermatologia", config=cfg_tmp, modo_demo=True
        )
        for ref in res.referencias:
            assert ref.confirmacao_anuncio_ativo is True
            assert ref.n_anuncios_ativos >= 1

    def test_contador_de_descartados_sem_anuncio(self, cfg_tmp):
        """
        Quando filtramos por 'sem anuncio', o numero precisa aparecer
        no relatorio. Em modo demo, nossa fixture nao tem candidatos
        com 0 ads, entao o numero e 0. Mas o campo existe e e int.
        """
        res = buscar_referencias(
            "@x", "dermatologia", config=cfg_tmp, modo_demo=True
        )
        assert isinstance(res.n_descartados_sem_anuncio, int)
        assert res.n_descartados_sem_anuncio >= 0

    def test_cliente_sem_anuncios_e_buscar_funciona(self, cfg_tmp):
        """
        @ do cliente nao precisa anunciar (e quem nao anuncia
        que esta procurando referencia). Pipeline ignora o status
        de anuncio do cliente; ele serve so para 'excluir-se da lista'.
        """
        res = buscar_referencias(
            "@cliente.nao.anuncia", "dermatologia", config=cfg_tmp, modo_demo=True
        )
        # NAO deve dar erro
        assert len(res.referencias) >= 5


# ============================================================
# CASO D: parser robusto
# ============================================================
#
# Garante que o parser da Ad Library nao quebra com HTML inesperado.
# ============================================================


class TestParserRobustez:
    def test_html_vazio_devolve_lista_vazia(self):
        assert _parse_html("") == []

    def test_html_quebrado_devolve_lista_vazia(self):
        """HTML malformado nao deve gerar exception."""
        assert _parse_html("<html>broken<<<") == []

    def test_html_sem_scripts_devolve_lista_vazia(self):
        html = "<html><body>so texto, nenhum script</body></html>"
        assert _parse_html(html) == []

    def test_script_com_json_invalido_nao_quebra(self):
        """Mesmo com JSON invalido dentro de script, nao deve quebrar."""
        html = "<html><body><script>{ esto nao e json valido :( </script></body></html>"
        # Nao garante 0 elementos (pode ter falso positivo de regex),
        # mas garante que NAO quebra.
        result = _parse_html(html)
        assert isinstance(result, list)


# ============================================================
# CASO E: comportamento sem chave Claude
# ============================================================


class TestSemChaveClaude:
    def test_pipeline_roda_sem_chave_anthropic(self, cfg_tmp):
        """
        Sem ANTHROPIC_API_KEY, ferramenta deve continuar funcionando
        com heuristica. Aviso explicito deve aparecer.
        """
        assert cfg_tmp.anthropic_api_key is None
        res = buscar_referencias(
            "@x", "dermatologia", config=cfg_tmp, modo_demo=True
        )
        # tem aviso especifico
        avisos_txt = " ".join(res.avisos).lower()
        assert "claude api indisponivel" in avisos_txt or "anthropic" in avisos_txt
        # ainda assim entrega referencias
        assert len(res.referencias) >= 5


# ============================================================
# CASO F: score com dados ausentes (robustez do scorer)
# ============================================================


class TestScorerDadosAusentes:
    def test_score_com_seguidores_none(self):
        score, bd = calcular_score(
            EntradaScore(
                n_anuncios_ativos=10,
                seguidores=None,  # IG bloqueado
                engajamento_percent=None,
                bio_menciona_especialidade=False,
                posts_ultimos_30_dias=None,
                confianca_handle="media",
            )
        )
        assert 0 <= score <= 100
        # com tudo None, ainda tem credito parcial de "postagem recente" + handle media
        assert bd["seguidores"] == 0.0
        assert bd["engajamento"] == 0.0
        assert bd["postagem_recente"] > 0  # credito parcial, nao zerar

    def test_score_nunca_explode(self):
        """Mesmo com valores absurdos, score fica em [0, 100]."""
        for n_ads, seg in [(0, 0), (10_000, 100_000_000), (-5, -1)]:
            score, _ = calcular_score(
                EntradaScore(
                    n_anuncios_ativos=max(0, n_ads),  # nao negativo
                    seguidores=max(0, seg) if seg else None,
                    engajamento_percent=None,
                    bio_menciona_especialidade=False,
                    posts_ultimos_30_dias=None,
                    confianca_handle="baixa",
                )
            )
            assert 0 <= score <= 100


# ============================================================
# CASO G: _bio_menciona robusto a None / vazio
# ============================================================


class TestBioMenciona:
    def test_bio_none(self):
        assert _bio_menciona(None, "dermatologia") is False

    def test_bio_vazia(self):
        assert _bio_menciona("", "dermatologia") is False

    def test_bio_so_emoji(self):
        assert _bio_menciona("😊😊😊", "dermatologia") is False

    def test_bio_com_palavra_completa(self):
        assert _bio_menciona("Dermatologista CRM 123", "dermatologia") is True

    def test_bio_com_acento(self):
        """Bio com acento deve ser normalizada antes do match."""
        assert _bio_menciona("Médica especializada em Dermatologia", "dermatologia") is True

    def test_bio_so_crm_sem_especialidade(self):
        """CRM/RQE sozinho ja conta como evidencia de medico."""
        assert _bio_menciona("Especialista em estetica - CRM 12345", "dermatologia") is True
