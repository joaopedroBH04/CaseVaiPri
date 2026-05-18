"""Interface web Streamlit do buscador de referencias.

Rode com:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# Permite rodar `streamlit run app/streamlit_app.py` mesmo sem instalar o pacote.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vaipri_ref.config import carregar  # noqa: E402
from vaipri_ref.pipeline import buscar_referencias  # noqa: E402
from vaipri_ref.reporter import gerar_markdown, salvar  # noqa: E402


# ============= Helpers (definidos antes do uso) =============


def _fmt_int(v):
    if v is None:
        return "n/d"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        return f"{v/1_000:.1f}k".replace(".0k", "k")
    return str(v)


def _fmt_pct(v):
    if v is None:
        return "n/d"
    return f"{v:.1f}%"


# ============= Setup =============

st.set_page_config(
    page_title="VaiPri — Buscador de Referencias",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
.stApp { background: #0b0d12; }
section[data-testid="stSidebar"] { background: #0e1219; border-right: 1px solid #1c2230; }
.title-strip { padding: 18px 0 6px; }
.title-strip h1 { color: #e7ecf2; margin: 0; }
.title-strip p { color: #8b95a7; margin: 4px 0 0; }
.ref-card {
  background: #141821; border: 1px solid #232a36;
  border-radius: 14px; padding: 16px; margin-bottom: 12px;
}
.ref-name { color: #e7ecf2; font-weight: 700; font-size: 17px; }
.ref-handle a { color: #5eead4; text-decoration: none; }
.score-pill {
  background: rgba(94,234,212,0.08); border: 1px solid rgba(94,234,212,0.3);
  color: #5eead4; padding: 4px 10px; border-radius: 99px;
  font-weight: 700; font-size: 14px; display: inline-block;
}
.bad-pill {
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.3);
  color: #f87171; padding: 4px 10px; border-radius: 99px;
  font-weight: 700; font-size: 14px;
}
.metric-mini { color: #8b95a7; font-size: 13px; margin-right: 14px; }
.metric-mini b { color: #e7ecf2; }
.note { color: #fbbf24; font-size: 12px; }
.section-header {
  color: #818cf8; font-weight: 700; text-transform: uppercase;
  font-size: 12px; letter-spacing: 0.05em; margin-top: 18px; margin-bottom: 8px;
}
hr { border-color: #232a36; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============= Sidebar =============

with st.sidebar:
    st.markdown("### Buscador VaiPri")
    st.caption("Achar 10 medicos da mesma especialidade do cliente que **rodam anuncios ativos agora**.")
    st.markdown("---")

    handle_cliente = st.text_input(
        "@ do cliente",
        value="@clinica.exemplo",
        help="Pode ser '@dra.fulana' ou a URL completa do Instagram.",
    )

    especialidade = st.selectbox(
        "Especialidade",
        options=["dermatologia", "nutrologia", "ortopedia", "ginecologia",
                 "cardiologia", "psiquiatria", "odontologia",
                 "cirurgia plastica", "outra (digitar)"],
        index=0,
    )
    if especialidade == "outra (digitar)":
        especialidade = st.text_input("Digite a especialidade:", value="dermatologia")

    cfg = carregar()
    st.markdown("---")
    st.markdown("### Modo")

    modo_demo = st.toggle(
        "Modo DEMO (fixtures sinteticas)",
        value=not cfg.tem_chave_anthropic,
        help=(
            "Ativa para validar a logica usando dados ficticios "
            "(util quando a rede bloqueia Meta). Desativa para scraping real."
        ),
    )

    if not cfg.tem_chave_anthropic:
        st.warning(
            "ANTHROPIC_API_KEY nao configurada. "
            "Match de especialidade vai usar heuristica de palavras-chave.",
            icon=":material/warning:",
        )

    st.markdown("---")
    rodar = st.button("Buscar referencias", type="primary", use_container_width=True)


# ============= Header =============

st.markdown(
    """
    <div class="title-strip">
        <h1>Referencias de trafego pago</h1>
        <p>De minutos no Ad Library + planilha pra <b>3 minutos automaticos</b>.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============= Execucao =============

if rodar:
    if not handle_cliente.strip() or not especialidade.strip():
        st.error("Informe o @ do cliente e a especialidade.")
        st.stop()

    progress = st.progress(0.0, text="iniciando")
    log = st.empty()

    def on_progress(etapa: str, info: dict) -> None:
        pct_map = {
            "inicio": (0.05, "iniciando"),
            "termos": (0.10, "gerando termos de busca"),
            "ad_library": (0.25, "consultando Meta Ad Library"),
            "ad_library_demo": (0.25, "carregando fixtures de demonstracao"),
            "fim": (0.99, "finalizando"),
        }
        if etapa == "candidato":
            i = info.get("i", 1)
            total = info.get("total", 1) or 1
            pct = 0.3 + 0.6 * (i / total)
            progress.progress(pct, text=f"avaliando {i}/{total}: {info.get('fb_page_name','?')[:40]}")
            return
        pct, label = pct_map.get(etapa, (None, etapa))
        if pct is not None:
            progress.progress(pct, text=label)

    try:
        resultado = buscar_referencias(
            handle_cliente=handle_cliente,
            especialidade=especialidade,
            on_progress=on_progress,
            modo_demo=modo_demo,
        )
        progress.progress(1.0, text="pronto")
    except Exception as exc:
        progress.empty()
        st.error(f"Erro na execucao: {exc}")
        st.stop()

    # ============= Sumario =============

    st.markdown('<div class="section-header">Sumario</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Candidatos brutos (Ad Library)", resultado.n_candidatos_brutos)
    col2.metric("Filtrados por especialidade", resultado.n_filtrados_por_especialidade)
    col3.metric("Sem anuncio ativo", resultado.n_descartados_sem_anuncio)
    col4.metric("Referencias finais", len(resultado.referencias))

    if resultado.avisos:
        for a in resultado.avisos:
            st.warning(a, icon=":material/warning:")

    if resultado.lista_incompleta and resultado.justificativa_lista_incompleta:
        st.error(
            f"**Lista parcial.** {resultado.justificativa_lista_incompleta}",
            icon=":material/error:",
        )

    with st.expander("Termos de busca usados na Ad Library"):
        st.code(" • ".join(resultado.termos_busca_usados), language="text")

    # ============= Lista =============

    st.markdown('<div class="section-header">Referencias ranqueadas</div>', unsafe_allow_html=True)

    if not resultado.referencias:
        st.info("Nenhuma referencia encontrada com os criterios atuais.")
    else:
        for i, ref in enumerate(resultado.referencias, start=1):
            with st.container():
                cols = st.columns([0.55, 0.3, 0.15])
                with cols[0]:
                    st.markdown(
                        f"""
                        <div class="ref-card">
                            <div class="ref-name">#{i} {ref.nome_exibicao or ref.instagram_handle}</div>
                            <div class="ref-handle"><a href="{ref.instagram_url}" target="_blank">@{ref.instagram_handle}</a></div>
                            <div style="margin-top:8px;">
                                <span class="metric-mini">seguidores <b>{_fmt_int(ref.metricas.seguidores)}</b></span>
                                <span class="metric-mini">posts <b>{_fmt_int(ref.metricas.total_posts)}</b></span>
                                <span class="metric-mini">engaj. (est) <b>{_fmt_pct(ref.metricas.engajamento_estimado_percent)}</b></span>
                                <span class="metric-mini">ads ativos <b>{ref.n_anuncios_ativos}</b></span>
                            </div>
                            <div style="margin-top:8px; color:#8b95a7; font-size:12.5px;">
                                <i>{ref.especialidade_justificativa or ''}</i>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if ref.notas:
                        for n in ref.notas:
                            st.caption(f":material/info: {n}")

                with cols[1]:
                    st.markdown(f"**Match de especialidade**")
                    st.progress(ref.especialidade_confianca, text=f"{int(ref.especialidade_confianca*100)}%")
                    st.markdown(f"**Confianca do handle:** `{ref.confianca_handle}`")
                    with st.expander("Score breakdown"):
                        bd = ref.score_breakdown or {}
                        df = pd.DataFrame(
                            [{"parcela": k, "pontos": round(v, 2)} for k, v in bd.items()]
                        )
                        st.dataframe(df, hide_index=True, use_container_width=True)

                with cols[2]:
                    st.markdown(
                        f"""
                        <div class="score-pill" style="font-size:22px; padding:14px 18px;">
                          {ref.score:.0f} / 100
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"[abrir anuncios →]({ref.biblioteca_anuncios_url})"
                    )

    # ============= Downloads =============

    st.markdown('<div class="section-header">Exportar</div>', unsafe_allow_html=True)
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    json_str = resultado.como_json()
    md_str = gerar_markdown(resultado)

    base = f"referencias_{especialidade}_{handle_cliente.lstrip('@')}".replace(" ", "-")

    col_dl1.download_button(
        "Baixar JSON",
        data=json_str,
        file_name=f"{base}.json",
        mime="application/json",
        use_container_width=True,
    )
    col_dl2.download_button(
        "Baixar Markdown",
        data=md_str,
        file_name=f"{base}.md",
        mime="text/markdown",
        use_container_width=True,
    )

    # CSV planilha
    rows = []
    for r in resultado.referencias:
        rows.append(
            {
                "instagram": "@" + r.instagram_handle,
                "instagram_url": str(r.instagram_url),
                "anuncios_ativos": r.n_anuncios_ativos,
                "biblioteca_url": str(r.biblioteca_anuncios_url),
                "seguidores": r.metricas.seguidores,
                "total_posts": r.metricas.total_posts,
                "engajamento_pct": r.metricas.engajamento_estimado_percent,
                "match_especialidade": r.especialidade_match,
                "match_confianca": r.especialidade_confianca,
                "score": r.score,
                "justificativa": r.especialidade_justificativa,
            }
        )
    df_csv = pd.DataFrame(rows)
    col_dl3.download_button(
        "Baixar CSV (planilha)",
        data=df_csv.to_csv(index=False).encode("utf-8"),
        file_name=f"{base}.csv",
        mime="text/csv",
        use_container_width=True,
    )

else:
    st.info(
        "Preencha @ do cliente + especialidade na barra lateral e clique em "
        "**Buscar referencias**. Em modo DEMO voce nao precisa de rede para Meta.",
        icon=":material/info:",
    )
