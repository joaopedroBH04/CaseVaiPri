"""Gera saidas em JSON, Markdown e HTML.

JSON: contrato programatico.
Markdown: facil de colar em Notion/email.
HTML: visualizacao bonita para demo / loom.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, BaseLoader, select_autoescape

from vaipri_ref.models import Resultado
from vaipri_ref.utils.normalize import slug


# ---------- Markdown ----------


def gerar_markdown(res: Resultado) -> str:
    L = []
    L.append(f"# Referencias para `{res.handle_cliente}` — {res.especialidade.title()}")
    L.append("")
    L.append(f"- Pais: **{res.pais}**")
    L.append(f"- Gerado em (UTC): **{res.gerado_em.isoformat()}**")
    L.append(f"- Candidatos brutos da Ad Library: **{res.n_candidatos_brutos}**")
    L.append(f"- Filtrados por especialidade errada: **{res.n_filtrados_por_especialidade}**")
    L.append(f"- Sem anuncio ativo: **{res.n_descartados_sem_anuncio}**")
    L.append("")

    if res.avisos:
        L.append("## Avisos do pipeline")
        for a in res.avisos:
            L.append(f"- {a}")
        L.append("")

    if res.lista_incompleta and res.justificativa_lista_incompleta:
        L.append("## Lista incompleta")
        L.append("")
        L.append("> " + res.justificativa_lista_incompleta)
        L.append("")

    L.append("## Termos de busca usados na Ad Library")
    L.append("")
    L.append(", ".join(f"`{t}`" for t in res.termos_busca_usados) or "_nenhum_")
    L.append("")

    if not res.referencias:
        L.append("**Nenhuma referencia encontrada.**")
        return "\n".join(L)

    L.append("## Top referencias")
    L.append("")
    for i, ref in enumerate(res.referencias, start=1):
        m = ref.metricas
        L.append(f"### {i}. {ref.nome_exibicao or ref.instagram_handle or ref.fb_page_name}")
        L.append("")
        if ref.instagram_handle:
            L.append(f"- **Instagram**: [@{ref.instagram_handle}]({ref.instagram_url})")
        else:
            L.append("- **Instagram**: _nao resolvido automaticamente — abra a Biblioteca de Anuncios para localizar_")
        L.append(f"- **Facebook Page**: {ref.fb_page_name} (`id={ref.fb_page_id}`)")
        L.append(f"- **Anuncios ativos agora**: {ref.n_anuncios_ativos}")
        L.append(f"- **Biblioteca de Anuncios**: [abrir]({ref.biblioteca_anuncios_url})")
        L.append(f"- **Seguidores**: {_fmt_int(m.seguidores)}")
        L.append(f"- **Engajamento estimado**: {_fmt_pct(m.engajamento_estimado_percent)}")
        L.append(f"- **Posts totais**: {_fmt_int(m.total_posts)}")
        L.append(f"- **Match de especialidade**: {ref.especialidade_match} "
                 f"({ref.especialidade_confianca * 100:.0f}% — {ref.especialidade_justificativa})")
        L.append(f"- **Score**: **{ref.score:.1f}/100**")
        L.append(f"  - breakdown: {ref.score_breakdown}")
        if ref.notas:
            L.append("- **Notas**:")
            for n in ref.notas:
                L.append(f"  - {n}")
        L.append("")

    return "\n".join(L)


# ---------- HTML ----------


_HTML_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Referencias — {{ res.especialidade.title() }}</title>
<style>
  :root {
    --bg: #0b0d12;
    --card: #141821;
    --muted: #8b95a7;
    --text: #e7ecf2;
    --accent: #5eead4;
    --accent-2: #818cf8;
    --warn: #fbbf24;
    --err: #f87171;
    --ok: #34d399;
    --line: #232a36;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text);
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    margin: 0; padding: 32px 24px 64px;
  }
  .wrap { max-width: 1080px; margin: 0 auto; }
  h1 { font-size: 24px; margin: 0 0 4px; }
  .sub { color: var(--muted); margin-bottom: 24px; }
  .kpis {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr));
    gap: 12px; margin-bottom: 24px;
  }
  .kpi {
    background: var(--card); border: 1px solid var(--line);
    border-radius: 12px; padding: 14px 16px;
  }
  .kpi b { font-size: 22px; display:block; }
  .kpi span { color: var(--muted); font-size: 12px; }
  .avisos {
    background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.4);
    color: var(--warn); border-radius: 10px; padding: 10px 14px; margin-bottom: 16px;
  }
  .incompleta {
    background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.4);
    color: var(--err); border-radius: 10px; padding: 10px 14px; margin-bottom: 16px;
  }
  .termos { color: var(--muted); margin-bottom: 24px; font-size: 13px; }
  .termos code {
    background: var(--card); padding: 2px 6px; border-radius: 6px;
    border: 1px solid var(--line); margin-right: 4px;
  }
  .ref {
    display: grid; grid-template-columns: 56px 1fr 200px;
    gap: 16px; align-items: center;
    background: var(--card); border: 1px solid var(--line);
    border-radius: 14px; padding: 16px; margin-bottom: 12px;
  }
  .avatar {
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg,var(--accent),var(--accent-2));
    display:flex; align-items:center; justify-content:center;
    color: #0b0d12; font-weight: 700; font-size: 18px;
    overflow: hidden;
  }
  .avatar img { width: 100%; height: 100%; object-fit: cover; }
  .meta h3 { margin: 0 0 2px; font-size: 16px; }
  .meta .handle a { color: var(--accent); text-decoration: none; }
  .meta .handle a:hover { text-decoration: underline; }
  .meta .row { color: var(--muted); font-size: 12.5px; margin-top: 6px; display: flex; flex-wrap: wrap; gap: 14px; }
  .meta .row span { display: inline-flex; gap: 6px; align-items: center; }
  .meta .row b { color: var(--text); }
  .score-box {
    background: rgba(94,234,212,0.06); border: 1px solid rgba(94,234,212,0.25);
    border-radius: 12px; padding: 12px; text-align: center;
  }
  .score-box .score { font-size: 28px; font-weight: 700; color: var(--accent); }
  .score-box .score small { font-size: 12px; color: var(--muted); font-weight: 500; }
  .score-box a { color: var(--accent-2); font-size: 12px; display:block; margin-top: 6px; text-decoration: none; }
  .score-box a:hover { text-decoration: underline; }
  details { margin-top: 8px; }
  summary { color: var(--muted); cursor: pointer; font-size: 12px; }
  .bd-list { font-size: 12px; color: var(--muted); margin-top: 4px; padding-left: 14px; }
  .bd-list li { margin: 2px 0; }
  .notas { color: var(--warn); font-size: 12px; margin-top: 6px; }
  footer { color: var(--muted); font-size: 12px; margin-top: 28px; text-align: center; }
  .badge {
    display:inline-block; padding: 2px 8px; border-radius: 99px;
    font-size: 11px; font-weight: 600; border: 1px solid var(--line);
  }
  .badge.ok { color: var(--ok); border-color: rgba(52,211,153,0.5); }
  .badge.warn { color: var(--warn); border-color: rgba(251,191,36,0.5); }
</style>
</head>
<body>
  <div class="wrap">
    <h1>Referencias para <code>@{{ res.handle_cliente }}</code> — {{ res.especialidade.title() }}</h1>
    <div class="sub">
      Gerado em {{ res.gerado_em.strftime("%Y-%m-%d %H:%M UTC") }}
      &middot; pais {{ res.pais }}
      &middot; {{ res.referencias|length }} referencia(s)
    </div>

    <div class="kpis">
      <div class="kpi"><b>{{ res.n_candidatos_brutos }}</b><span>Candidatos brutos (Ad Library)</span></div>
      <div class="kpi"><b>{{ res.n_filtrados_por_especialidade }}</b><span>Filtrados por especialidade</span></div>
      <div class="kpi"><b>{{ res.n_descartados_sem_anuncio }}</b><span>Descartados sem anuncio ativo</span></div>
      <div class="kpi"><b>{{ res.referencias|length }}</b><span>Referencias finais</span></div>
    </div>

    {% if res.avisos %}
      <div class="avisos">
        <b>Avisos:</b>
        <ul>
          {% for a in res.avisos %}<li>{{ a }}</li>{% endfor %}
        </ul>
      </div>
    {% endif %}

    {% if res.lista_incompleta and res.justificativa_lista_incompleta %}
      <div class="incompleta">
        <b>Lista parcial:</b> {{ res.justificativa_lista_incompleta }}
      </div>
    {% endif %}

    <div class="termos">
      <b>Termos buscados na Ad Library:</b>
      {% for t in res.termos_busca_usados %}<code>{{ t }}</code>{% endfor %}
    </div>

    {% for ref in res.referencias %}
      <div class="ref">
        <div class="avatar">
          {% if ref.metricas.foto_url %}
            <img src="{{ ref.metricas.foto_url }}" alt=""/>
          {% else %}{{ (ref.nome_exibicao or ref.instagram_handle or ref.fb_page_name)[0]|upper }}{% endif %}
        </div>
        <div class="meta">
          <h3>{{ ref.nome_exibicao or ref.instagram_handle or ref.fb_page_name }}</h3>
          <div class="handle">
            {% if ref.instagram_handle %}
              <a href="{{ ref.instagram_url }}" target="_blank" rel="noopener">@{{ ref.instagram_handle }}</a>
            {% else %}
              <span style="color:var(--muted)">[Instagram nao resolvido — ver Ad Library]</span>
            {% endif %}
            <span class="badge ok">match {{ "%.0f"|format(ref.especialidade_confianca * 100) }}%</span>
            {% if ref.confianca_handle != "alta" %}
              <span class="badge warn">handle: {{ ref.confianca_handle }}</span>
            {% endif %}
          </div>
          <div class="row">
            <span>seguidores <b>{{ fmt_int(ref.metricas.seguidores) }}</b></span>
            <span>posts <b>{{ fmt_int(ref.metricas.total_posts) }}</b></span>
            <span>engajamento (est.) <b>{{ fmt_pct(ref.metricas.engajamento_estimado_percent) }}</b></span>
            <span>anuncios ativos <b>{{ ref.n_anuncios_ativos }}</b></span>
          </div>
          {% if ref.especialidade_justificativa %}
            <div class="row">
              <span style="color:var(--muted)">justificativa: <i>{{ ref.especialidade_justificativa }}</i></span>
            </div>
          {% endif %}
          {% if ref.notas %}
            <div class="notas">
              {% for n in ref.notas %}&#9888; {{ n }}<br/>{% endfor %}
            </div>
          {% endif %}
          <details>
            <summary>breakdown do score</summary>
            <ul class="bd-list">
              {% for k, v in ref.score_breakdown.items() %}
                <li>{{ k }}: <b>{{ "%.1f"|format(v) }}</b></li>
              {% endfor %}
            </ul>
          </details>
        </div>
        <div class="score-box">
          <div class="score">{{ "%.0f"|format(ref.score) }}<small> / 100</small></div>
          <a href="{{ ref.biblioteca_anuncios_url }}" target="_blank" rel="noopener">ver anuncios &rarr;</a>
        </div>
      </div>
    {% endfor %}

    {% if not res.referencias %}
      <div class="incompleta"><b>Nenhuma referencia encontrada.</b></div>
    {% endif %}

    <footer>
      gerado pelo buscador de referencias VaiPri &middot; case Joao Pedro
    </footer>
  </div>
</body>
</html>
"""


def gerar_html(res: Resultado) -> str:
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    env.globals["fmt_int"] = _fmt_int
    env.globals["fmt_pct"] = _fmt_pct
    tmpl = env.from_string(_HTML_TEMPLATE)
    return tmpl.render(res=res)


# ---------- IO ----------


def salvar(res: Resultado, *, diretorio: Path | str = "outputs") -> dict[str, Path]:
    """Salva JSON, Markdown e HTML do resultado. Retorna os paths."""
    dir_path = Path(diretorio)
    dir_path.mkdir(parents=True, exist_ok=True)

    base = f"{slug(res.especialidade)}__{slug(res.handle_cliente)}"
    paths = {
        "json": dir_path / f"{base}.json",
        "md": dir_path / f"{base}.md",
        "html": dir_path / f"{base}.html",
    }
    paths["json"].write_text(res.como_json(), encoding="utf-8")
    paths["md"].write_text(gerar_markdown(res), encoding="utf-8")
    paths["html"].write_text(gerar_html(res), encoding="utf-8")
    return paths


# ---------- formatters ----------


def _fmt_int(v: int | None) -> str:
    if v is None:
        return "n/d"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        return f"{v/1_000:.1f}k".replace(".0k", "k")
    return str(v)


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "n/d"
    return f"{v:.1f}%"
