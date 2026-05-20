"""Interface web Streamlit do buscador de referências.

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
from vaipri_ref.reporter import gerar_markdown  # noqa: E402
from vaipri_ref.utils.normalize import limpar_handle  # noqa: E402


# ============= Helpers =============


def _fmt_int(v):
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        return f"{v/1_000:.1f}k".replace(".0k", "k")
    return str(v)


def _fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:.1f}%"


def _cor_score(score: float) -> str:
    """Cor do score baseada na nota (gradient verde > amarelo > vermelho)."""
    if score >= 8.5:
        return "#10b981"  # verde forte
    if score >= 7.0:
        return "#5eead4"  # ciano
    if score >= 5.5:
        return "#fbbf24"  # amarelo
    if score >= 4.0:
        return "#f59e0b"  # laranja
    return "#f87171"      # vermelho


# Tooltips das parcelas do score: cada chave aqui bate com a chave do
# breakdown gerado pelo scorer.py. Esse dict alimenta o atributo `title`
# do HTML, gerando um tooltip nativo do navegador.
TOOLTIPS_PARCELAS = {
    "Volume de anúncios rodando":
        "Quantos anúncios ativos esse médico tem agora. Mais ads = mais "
        "criativos diferentes pra você analisar e adaptar. Piso: 1 anúncio. "
        "Teto: 30+ (a partir daí satura).",
    "Tração no Instagram":
        "Quantidade de seguidores no Instagram. Indica que o perfil tem "
        "audiência consolidada. Piso: 1.000. Teto: 200.000.",
    "Engajamento real":
        "Soma de curtidas e comentários dos últimos posts dividido pelo total "
        "de seguidores. Acima de 1% é considerado bom (não inflado).",
    "Perfil ativo (posts recentes)":
        "Postou alguma coisa nos últimos 30 dias? Quem investe em ads mas "
        "abandonou o feed costuma ter funil quebrado.",
    "Identidade médica clara":
        "A bio ou nome menciona explicitamente a especialidade, CRM ou RQE? "
        "Isso confirma que é médico de verdade, não influenciador.",
    "Confiabilidade do match":
        "Quão certo nós estamos de que o @ do Instagram é REALMENTE deste "
        "médico (e não de outra pessoa). Alta = link direto do Facebook; "
        "Média = inferida pelo nome; Baixa = sem confirmação.",
}


def _render_referencia(i: int, ref) -> None:
    """Renderiza um card de referência com layout polido."""
    cor = _cor_score(ref.score)
    rotulo = ref.score_rotulo or "—"
    pct_match = int(ref.especialidade_confianca * 100)

    if ref.instagram_handle:
        link_html = (
            f'<a href="{ref.instagram_url}" target="_blank">'
            f'@{ref.instagram_handle}</a>'
        )
    else:
        link_html = (
            f'<a href="{ref.biblioteca_anuncios_url}" target="_blank" '
            f'style="color: var(--warn);">[Sem @ — ver Ad Library]</a>'
        )

    nome_card = ref.nome_exibicao or ref.instagram_handle or ref.fb_page_name

    # Layout: 2 colunas (card | score box)
    cols = st.columns([0.72, 0.28])

    with cols[0]:
        eng_display = _fmt_pct(ref.metricas.engajamento_estimado_percent)
        eng_help = (
            "Engajamento médio dos últimos posts (curtidas + comentários ÷ "
            "seguidores). Acima de 1% é considerado um perfil ativo e real."
        )
        justif = (ref.especialidade_justificativa or "").strip()

        st.markdown(
            f"""
            <div class="ref-card">
              <div class="ref-header">
                <div class="ref-rank">{i}</div>
                <div class="ref-info">
                  <div class="ref-name">{nome_card}</div>
                  <div class="ref-handle">{link_html}</div>
                </div>
              </div>

              <div class="metrics-row">
                <div class="metric-mini-card" title="Pessoas que seguem este médico no Instagram.">
                  <div class="metric-mini-label">Seguidores</div>
                  <div class="metric-mini-value">{_fmt_int(ref.metricas.seguidores)}</div>
                </div>
                <div class="metric-mini-card" title="Total de publicações no perfil (histórico).">
                  <div class="metric-mini-label">Posts (total)</div>
                  <div class="metric-mini-value">{_fmt_int(ref.metricas.total_posts)}</div>
                </div>
                <div class="metric-mini-card" title="{eng_help}">
                  <div class="metric-mini-label">Engajamento médio</div>
                  <div class="metric-mini-value">{eng_display}</div>
                </div>
                <div class="metric-mini-card" title="Quantos anúncios este médico tem rodando neste momento no Meta.">
                  <div class="metric-mini-label">Anúncios ativos</div>
                  <div class="metric-mini-value">{ref.n_anuncios_ativos}</div>
                </div>
              </div>

              <div class="match-line">
                <div class="match-label">
                  <span>Match de especialidade</span>
                  <b>{pct_match}%</b>
                </div>
                <div class="match-bar-bg">
                  <div class="match-bar-fill" style="width: {pct_match}%;"></div>
                </div>
              </div>

              {f'<div class="justificativa">{justif}</div>' if justif else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ref.notas:
            for n in ref.notas:
                st.markdown(f'<div class="note-card">⚠ {n}</div>', unsafe_allow_html=True)

        with st.expander(":material/analytics: Por que essa nota?"):
            bd = ref.score_breakdown or {}
            pesos_max = {
                "Volume de anúncios rodando": 2.5,
                "Tração no Instagram": 2.0,
                "Engajamento real": 1.5,
                "Perfil ativo (posts recentes)": 1.5,
                "Identidade médica clara": 1.5,
                "Confiabilidade do match": 1.0,
            }
            items_html = ""
            for criterio, valor in bd.items():
                peso = pesos_max.get(criterio, 1.0)
                pct = (valor / peso * 100) if peso else 0
                tooltip = TOOLTIPS_PARCELAS.get(criterio, criterio).replace('"', '&quot;')
                if valor == int(valor):
                    valor_str = f"{int(valor)}/{int(peso) if peso == int(peso) else peso:g}"
                else:
                    valor_str = f"{valor:.1f}/{peso:g}"
                items_html += f"""
                <div class="bd-item">
                  <div class="bd-item-head">
                    <span class="bd-item-name" title="{tooltip}">{criterio}</span>
                    <span class="bd-item-score">{valor_str}</span>
                  </div>
                  <div class="bd-item-bar-bg">
                    <div class="bd-item-bar-fill" style="width: {pct}%;"></div>
                  </div>
                </div>
                """
            st.markdown(
                f"""
                <p style="color: var(--text-secondary); font-size: 13px; margin: 4px 0 8px;">
                  Cada parcela contribui com até X pontos. Passe o mouse para entender cada critério.
                </p>
                <div class="bd-grid">{items_html}</div>
                """,
                unsafe_allow_html=True,
            )

    with cols[1]:
        st.markdown(
            f"""
            <div class="score-box">
              <div class="score-big" style="color: {cor};">
                {ref.score:.1f}<span class="score-suffix"> / 10</span>
              </div>
              <div class="score-label" style="color: {cor};">{rotulo}</div>
              <a class="score-link" href="{ref.biblioteca_anuncios_url}" target="_blank" rel="noopener">
                Ver anúncios →
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============= Setup =============

st.set_page_config(
    page_title="VaiPri — Buscador de Referências",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": None, "Get help": None, "Report a bug": None},
)

CUSTOM_CSS = """
<style>
:root {
  --bg-primary: #0a0c14;
  --bg-card: #121620;
  --bg-elevated: #1a1f2e;
  --border: #232a3a;
  --border-strong: #2f3849;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent: #5eead4;
  --accent-soft: rgba(94, 234, 212, 0.1);
  --accent-2: #818cf8;
  --success: #10b981;
  --warn: #fbbf24;
  --danger: #f87171;
}

/* Fundo geral */
.stApp {
  background: radial-gradient(ellipse at top, #0d1018 0%, #07090e 100%);
  color: var(--text-primary);
}

/* Esconde footer "Made with Streamlit", menu hamburger e Deploy */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}

/* Esconde a sidebar "Pages" automatica quando so tem 1 page */
section[data-testid="stSidebarNav"] {display: none;}

/* Sidebar custom */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0e1219 0%, #0a0c14 100%);
  border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown h3 {
  color: var(--text-primary);
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  margin-top: 8px;
}
section[data-testid="stSidebar"] hr {
  border-color: var(--border) !important;
  margin: 16px 0;
}

/* Inputs */
.stTextInput input, .stSelectbox > div > div {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 10px !important;
}
.stTextInput input:focus, .stSelectbox > div > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-soft) !important;
}

/* Botão primário */
.stButton button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent) 0%, #4dd6c2 100%) !important;
  color: #0a0c14 !important;
  font-weight: 700 !important;
  border: 0 !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
  transition: all 0.2s;
}
.stButton button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(94, 234, 212, 0.3);
}

/* Header da pagina */
.title-strip {
  padding: 28px 0 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
}
.title-strip h1 {
  color: var(--text-primary);
  margin: 0;
  font-size: 36px;
  letter-spacing: -0.02em;
  font-weight: 800;
}
.title-strip h1 span.accent {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.title-strip p {
  color: var(--text-secondary);
  margin: 8px 0 0;
  font-size: 15px;
}

/* Secao header */
.section-header {
  color: var(--accent-2);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.12em;
  margin-top: 24px;
  margin-bottom: 14px;
}

/* KPIs */
[data-testid="stMetric"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px;
}
[data-testid="stMetricLabel"] p {
  color: var(--text-secondary) !important;
  font-size: 12px !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
  font-size: 32px !important;
  font-weight: 700 !important;
}

/* Card de referencia */
.ref-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 14px;
  transition: all 0.2s;
}
.ref-card:hover {
  border-color: var(--border-strong);
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.ref-header {
  display: flex; align-items: flex-start; gap: 14px;
  margin-bottom: 12px;
}
.ref-rank {
  width: 32px; height: 32px;
  background: linear-gradient(135deg, var(--accent-2), var(--accent));
  color: #0a0c14; font-weight: 800;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.ref-info { flex: 1; min-width: 0; }
.ref-name {
  color: var(--text-primary);
  font-weight: 700;
  font-size: 17px;
  margin: 0;
}
.ref-handle {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 2px;
}
.ref-handle a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 500;
}
.ref-handle a:hover { text-decoration: underline; }

/* Metricas mini dentro do card */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.metric-mini-card {
  background: var(--bg-elevated);
  border-radius: 10px;
  padding: 10px 12px;
}
.metric-mini-label {
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}
.metric-mini-value {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 700;
}

/* Justificativa */
.justificativa {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
  font-style: italic;
}

/* Score box */
.score-box {
  background: var(--bg-elevated);
  border-radius: 14px;
  padding: 16px;
  text-align: center;
  border: 1px solid var(--border);
}
.score-big {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.02em;
}
.score-suffix {
  font-size: 16px;
  color: var(--text-muted);
  font-weight: 500;
}
.score-label {
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.score-link {
  display: inline-block;
  margin-top: 10px;
  background: var(--accent-soft);
  color: var(--accent) !important;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
}
.score-link:hover {
  background: rgba(94, 234, 212, 0.2);
  transform: translateY(-1px);
}

/* Match progress bar */
.match-line {
  margin-top: 14px;
}
.match-label {
  display: flex; justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}
.match-label b { color: var(--text-primary); }
.match-bar-bg {
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 99px;
  overflow: hidden;
}
.match-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-2), var(--accent));
  border-radius: 99px;
}

/* Breakdown box (expander custom) */
.bd-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 12px;
}
.bd-item {
  background: var(--bg-elevated);
  border-radius: 10px;
  padding: 12px;
  border: 1px solid var(--border);
}
.bd-item-head {
  display: flex; justify-content: space-between; align-items: center;
  gap: 8px;
}
.bd-item-name {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: help;
  border-bottom: 1px dotted var(--border-strong);
}
.bd-item-score {
  color: var(--text-primary);
  font-weight: 700;
  font-size: 16px;
}
.bd-item-bar-bg {
  margin-top: 8px;
  height: 4px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
}
.bd-item-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-2), var(--accent));
  border-radius: 99px;
}

/* Note (info amarela embaixo do card) */
.note-card {
  background: rgba(251, 191, 36, 0.06);
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 10px;
  padding: 10px 12px;
  margin-top: 10px;
  color: var(--warn);
  font-size: 12px;
}

/* Avisos amarelos do Streamlit */
.stAlert {
  border-radius: 12px !important;
}

/* Download buttons */
.stDownloadButton button {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
.stDownloadButton button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============= Sidebar =============

with st.sidebar:
    st.markdown("### Buscador VaiPri")
    st.caption("Achar até 10 médicos da mesma especialidade do cliente que **rodam anúncios ativos agora**.")
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
        "Modo DEMO (fixtures sintéticas)",
        value=False,
        help=(
            "Ativa para validar a lógica usando dados fictícios "
            "(útil quando a rede bloqueia Meta). Desativa para buscar dados reais."
        ),
    )

    st.markdown("---")
    rodar = st.button("Buscar referências", type="primary", use_container_width=True)


# ============= Header =============

st.markdown(
    """
    <div class="title-strip">
        <h1>Buscador de <span class="accent">referências</span> de tráfego pago</h1>
        <p>De minutos no Ad Library + planilha para <b>3 minutos automáticos</b>.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============= Execução =============

if rodar:
    # Robustez: valida input ANTES de rodar (modificação 11)
    if not handle_cliente.strip() or not especialidade.strip():
        st.error("Informe o @ do cliente e a especialidade.")
        st.stop()

    try:
        limpar_handle(handle_cliente)
    except ValueError as exc:
        st.error(
            f"@ do cliente inválido: {exc}. "
            "Use formato '@dra.fulana' ou cole a URL completa do Instagram."
        )
        st.stop()

    if len(especialidade.strip()) < 3:
        st.error("Especialidade muito curta. Use ao menos 3 caracteres.")
        st.stop()

    progress = st.progress(0.0, text="iniciando")

    def on_progress(etapa: str, info: dict) -> None:
        pct_map = {
            "inicio": (0.05, "iniciando"),
            "termos": (0.10, "gerando termos de busca"),
            "ad_library": (0.20, "consultando Meta Ad Library"),
            "ad_library_demo": (0.25, "carregando fixtures de demonstração"),
            "apify_ig": (0.65, "buscando métricas reais no Instagram (Apify)"),
            "fim": (0.99, "finalizando"),
        }
        if etapa == "candidato":
            i = info.get("i", 1)
            total = info.get("total", 1) or 1
            pct = 0.3 + 0.35 * (i / total)
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
        st.error(f"Erro na execução: {exc}")
        st.stop()

    # ============= Sumário (apenas 2 KPIs, modificação 1) =============

    st.markdown('<div class="section-header">Sumário</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    col1.metric("Candidatos brutos (Ad Library)", resultado.n_candidatos_brutos)
    col2.metric("Referências finais", len(resultado.referencias))

    # Avisos do pipeline (modificação 2 e 7: anthropic warning sumiu do pipeline)
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

    st.markdown('<div class="section-header">Referências ranqueadas</div>', unsafe_allow_html=True)

    if not resultado.referencias:
        st.info("Nenhuma referência encontrada com os critérios atuais. Tente outra especialidade ou ative o modo DEMO.")
    else:
        for i, ref in enumerate(resultado.referencias, start=1):
            _render_referencia(i, ref)

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

    rows = []
    for r in resultado.referencias:
        rows.append(
            {
                "instagram": ("@" + r.instagram_handle) if r.instagram_handle else "(via Ad Library)",
                "instagram_url": str(r.instagram_url) if r.instagram_url else "",
                "anuncios_ativos": r.n_anuncios_ativos,
                "biblioteca_url": str(r.biblioteca_anuncios_url),
                "seguidores": r.metricas.seguidores,
                "total_posts": r.metricas.total_posts,
                "engajamento_pct": r.metricas.engajamento_estimado_percent,
                "match_especialidade": r.especialidade_match,
                "match_confianca": r.especialidade_confianca,
                "nota": r.score,
                "rotulo": r.score_rotulo,
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
        "Preencha o **@** do cliente + especialidade na barra lateral e clique em "
        "**Buscar referências**.",
        icon=":material/info:",
    )
