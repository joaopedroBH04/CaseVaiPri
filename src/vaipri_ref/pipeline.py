"""Pipeline principal: orquestra termos -> AdLibrary -> IG -> match -> score."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from vaipri_ref.ai.claude_client import ClaudeClient
from vaipri_ref.ai.specialty_matcher import SpecialtyMatcher
from vaipri_ref.config import Config, carregar
from vaipri_ref.demo import fixtures as demo_fixtures
from vaipri_ref.discovery.meta_ad_library import MetaAdLibraryScraper
from vaipri_ref.discovery.search_terms import gerar_termos
from vaipri_ref.instagram.handle_resolver import HandleResolver
from vaipri_ref.instagram.scraper import (
    InstagramScraper,
    PerfilIG,
    estimar_engajamento,
)
from vaipri_ref.models import Candidato, Metricas, Referencia, Resultado
from vaipri_ref.scorer import EntradaScore, calcular as calcular_score
from vaipri_ref.utils.cache import Cache
from vaipri_ref.utils.logger import configurar as configurar_logger, obter as obter_logger
from vaipri_ref.utils.normalize import limpar_handle, url_biblioteca_anuncios, url_perfil_ig


logger = obter_logger()


def buscar_referencias(
    handle_cliente: str,
    especialidade: str,
    *,
    config: Config | None = None,
    on_progress=None,  # callback: (etapa: str, info: dict) -> None
    modo_demo: bool = False,
) -> Resultado:
    """Roda o pipeline completo. E o ponto de entrada usado pela CLI e UI.

    on_progress: callback opcional invocado a cada etapa, util para UI/Streamlit.
    modo_demo: se True, usa fixtures sinteticas para descoberta e enriquecimento
               em vez de scraping real. O resto do pipeline (match + score) roda
               normalmente. Util quando o avaliador esta em rede que bloqueia Meta.
    """
    cfg = config or carregar()
    configurar_logger(cfg.verbose)

    try:
        handle_cliente_norm = limpar_handle(handle_cliente)
    except ValueError as exc:
        raise ValueError(f"Handle do cliente invalido: {exc}") from exc

    especialidade_norm = especialidade.strip().lower()
    if not especialidade_norm:
        raise ValueError("Especialidade vazia.")

    _emitir(on_progress, "inicio", {
        "handle_cliente": handle_cliente_norm,
        "especialidade": especialidade_norm,
        "pais": cfg.country,
    })

    cache = Cache(cfg.cache_dir)
    try:
        return _executar(
            cfg=cfg,
            cache=cache,
            handle_cliente_norm=handle_cliente_norm,
            especialidade_norm=especialidade_norm,
            on_progress=on_progress,
            modo_demo=modo_demo,
        )
    finally:
        # Fecha o SQLite do diskcache. Critico no Windows pra liberar
        # o lock do arquivo cache.db antes de qualquer rmtree do
        # diretorio (ex: TemporaryDirectory em testes).
        cache.close()


def _executar(
    *,
    cfg: Config,
    cache: Cache,
    handle_cliente_norm: str,
    especialidade_norm: str,
    on_progress,
    modo_demo: bool,
) -> Resultado:
    """Corpo do pipeline. Separado de `buscar_referencias` para garantir
    que o cache seja fechado mesmo em caso de excecao."""
    claude = ClaudeClient(api_key=cfg.anthropic_api_key, model=cfg.claude_model)
    avisos: list[str] = []
    if not claude.disponivel:
        avisos.append(
            "Claude API indisponivel (sem ANTHROPIC_API_KEY): "
            "validacao de especialidade e geracao de termos usaram heuristicas."
        )

    # 1) termos de busca
    _emitir(on_progress, "termos", {})
    termos = gerar_termos(especialidade_norm, claude=claude, n=10)
    logger.info("Termos de busca: %s", termos)

    # 2) Descoberta de candidatos. Real: scraping da Ad Library. Demo: fixtures.
    perfis_fixture: dict[str, PerfilIG] = {}
    if modo_demo:
        _emitir(on_progress, "ad_library_demo", {"especialidade": especialidade_norm})
        if not demo_fixtures.disponivel(especialidade_norm):
            avisos.append(
                f"Modo demo: nao ha fixture para {especialidade_norm!r}. "
                f"Disponiveis: {list(demo_fixtures.especialidades_disponiveis())}."
            )
            candidatos: list[Candidato] = []
        else:
            avisos.append(
                "Modo DEMO ativo: os perfis listados sao FICTICIOS, gerados para "
                "validar o pipeline offline. NAO use os handles em producao."
            )
            fixt = demo_fixtures.carregar(especialidade_norm)
            candidatos = []
            for f in fixt:
                candidatos.append(
                    Candidato(
                        fb_page_id=f.fb_page_id,
                        fb_page_name=f.fb_page_name,
                        fb_page_url=f.fb_page_url,
                        n_anuncios_ativos=f.n_anuncios_ativos,
                        instagram_handle_hint=f.instagram_handle,
                    )
                )
                perfis_fixture[f.instagram_handle] = PerfilIG(
                    handle=f.instagram_handle,
                    url=f"https://www.instagram.com/{f.instagram_handle}/",
                    seguidores=f.seguidores,
                    seguindo=f.seguindo,
                    total_posts=f.total_posts,
                    posts_ultimos_30_dias=f.posts_ultimos_30_dias,
                    nome_completo=f.nome_completo,
                    bio=f.bio,
                    foto_url=None,
                    metricas_completas=True,
                )
    else:
        _emitir(on_progress, "ad_library", {"termos": termos})
        scraper_meta = MetaAdLibraryScraper(
            cache=cache, country=cfg.country, headless=cfg.headless
        )
        candidatos = scraper_meta.buscar(termos, limite_por_termo=12)

    logger.info("Total de %d candidatos brutos da %s",
                len(candidatos),
                "fixture demo" if modo_demo else "Ad Library")

    # corta no max_candidatos
    candidatos = candidatos[: cfg.max_candidatos]

    if not candidatos and not modo_demo:
        avisos.append(
            "Nenhum candidato retornou da Ad Library. Possiveis causas: "
            "termos muito raros, bloqueio temporario da Meta ou rede offline. "
            "Tente novamente em alguns minutos, ou rode em modo --demo."
        )

    # 3) resolucao de handle + 4) enriquecimento IG + 5) match especialidade + 6) score
    resolver = HandleResolver(
        cache=cache, claude=claude, pular_validacao_http=modo_demo
    )
    ig_scraper = InstagramScraper(cache=cache)
    matcher = SpecialtyMatcher(claude=claude)

    referencias: list[Referencia] = []
    n_filtrados_especialidade = 0
    n_descartados_sem_anuncio = 0

    for i, cand in enumerate(candidatos, start=1):
        _emitir(
            on_progress,
            "candidato",
            {"i": i, "total": len(candidatos), "fb_page_name": cand.fb_page_name},
        )

        if cand.n_anuncios_ativos < 1:
            n_descartados_sem_anuncio += 1
            continue

        # 3a) resolve handle do IG
        handle_res = resolver.resolver(
            fb_page_id=cand.fb_page_id,
            fb_page_name=cand.fb_page_name,
            fb_page_url=str(cand.fb_page_url) if cand.fb_page_url else None,
            hint=cand.instagram_handle_hint,
        )

        if not handle_res.handle:
            logger.debug("Sem handle resolvido para %s, pulando", cand.fb_page_name)
            continue
        if handle_res.handle == handle_cliente_norm:
            logger.debug("Handle resolvido e o proprio cliente, pulando")
            continue

        # 3b) enriquece IG (em demo, usa fixture pre-carregado)
        if modo_demo and handle_res.handle in perfis_fixture:
            perfil = perfis_fixture[handle_res.handle]
        else:
            perfil = ig_scraper.buscar_perfil(handle_res.handle)

        # 4) match de especialidade
        match = matcher.avaliar(
            especialidade=especialidade_norm,
            nome=perfil.nome_completo,
            bio=perfil.bio,
            nome_fb_page=cand.fb_page_name,
        )
        if not match.match:
            n_filtrados_especialidade += 1
            continue

        # estima engajamento + cria metricas
        engaj = estimar_engajamento(perfil.seguidores)
        metricas = Metricas(
            seguidores=perfil.seguidores,
            seguindo=perfil.seguindo,
            total_posts=perfil.total_posts,
            engajamento_estimado_percent=engaj,
            posts_ultimos_30_dias=perfil.posts_ultimos_30_dias,
            bio=perfil.bio,
            nome_completo=perfil.nome_completo,
            foto_url=perfil.foto_url,
            metricas_completas=perfil.metricas_completas,
        )

        bio_menciona = _bio_menciona(perfil.bio, especialidade_norm)
        score, breakdown = calcular_score(
            EntradaScore(
                n_anuncios_ativos=cand.n_anuncios_ativos,
                seguidores=perfil.seguidores,
                engajamento_percent=engaj,
                bio_menciona_especialidade=bio_menciona,
                posts_ultimos_30_dias=perfil.posts_ultimos_30_dias,
                confianca_handle=handle_res.confianca,
            )
        )

        notas: list[str] = []
        if perfil.erro:
            notas.append(f"IG scraping parcial: {perfil.erro}")
        if handle_res.fonte == "claude_inferencia":
            notas.append("Handle do Instagram foi inferido pela IA e validado por HEAD request.")
        if not perfil.metricas_completas:
            notas.append("Algumas metricas de IG nao foram obtidas; ver `metricas.metricas_completas`.")

        try:
            ref = Referencia(
                instagram_handle=handle_res.handle,
                instagram_url=url_perfil_ig(handle_res.handle),
                nome_exibicao=perfil.nome_completo or cand.fb_page_name,
                fb_page_id=cand.fb_page_id,
                fb_page_name=cand.fb_page_name,
                n_anuncios_ativos=cand.n_anuncios_ativos,
                biblioteca_anuncios_url=url_biblioteca_anuncios(cand.fb_page_id, country=cfg.country),
                confirmacao_anuncio_ativo=True,
                metricas=metricas,
                especialidade_alvo=especialidade_norm,
                especialidade_match=True,
                especialidade_confianca=match.confianca,
                especialidade_justificativa=match.justificativa,
                score=score,
                score_breakdown=breakdown,
                confianca_handle=handle_res.confianca,
                notas=notas,
            )
        except Exception as exc:
            logger.warning("Falha criando Referencia para %s: %s", cand.fb_page_name, exc)
            continue

        referencias.append(ref)

    referencias.sort(key=lambda r: r.score, reverse=True)

    top = referencias[: cfg.top_n]

    lista_incompleta = len(top) < cfg.top_n
    justif_incompleta: str | None = None
    if lista_incompleta:
        justif_incompleta = (
            f"Foram encontradas apenas {len(top)} referencias que cumprem "
            f"TODOS os criterios (anuncio ativo, especialidade {especialidade_norm}, "
            "perfil acessivel). Conforme orientacao do case, NAO completamos a "
            "lista com perfis ruins. Total bruto de candidatos: "
            f"{len(candidatos)}; filtrados por especialidade: {n_filtrados_especialidade}; "
            f"sem anuncio ativo: {n_descartados_sem_anuncio}."
        )

    # Se a chave Claude existia mas a API rejeitou em runtime (401/403),
    # acrescenta aviso explicito pro usuario consertar o .env depois.
    if claude.aviso_fatal:
        avisos.append(claude.aviso_fatal)

    resultado = Resultado(
        handle_cliente=handle_cliente_norm,
        especialidade=especialidade_norm,
        pais=cfg.country,
        gerado_em=datetime.now(timezone.utc),
        referencias=top,
        n_candidatos_brutos=len(candidatos),
        n_filtrados_por_especialidade=n_filtrados_especialidade,
        n_descartados_sem_anuncio=n_descartados_sem_anuncio,
        termos_busca_usados=termos,
        lista_incompleta=lista_incompleta,
        justificativa_lista_incompleta=justif_incompleta,
        avisos=avisos,
    )

    _emitir(on_progress, "fim", {"n_referencias": len(top)})
    return resultado


# ------- helpers -------


def _bio_menciona(bio: str | None, especialidade: str) -> bool:
    if not bio:
        return False
    import unicodedata

    def norm(s: str) -> str:
        s = s.lower()
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return s

    bio_n = norm(bio)
    palavras = [especialidade] + especialidade.split()
    palavras += ["crm", "rqe"]  # registros profissionais
    return any(re.search(rf"\b{re.escape(norm(p))}", bio_n) for p in palavras if p)


def _emitir(callback, etapa: str, info: dict) -> None:
    if callback:
        try:
            callback(etapa, info)
        except Exception:
            pass
