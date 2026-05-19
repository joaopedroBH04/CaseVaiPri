"""CLI da ferramenta. Roda via `python -m vaipri_ref` ou `vaipri-ref`."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from vaipri_ref.config import carregar
from vaipri_ref.pipeline import buscar_referencias
from vaipri_ref.reporter import salvar


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Buscador de referencias de trafego pago para clinicas medicas.",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def buscar(
    handle: str = typer.Argument(..., help="@ do cliente, ex: @clinica.exemplo"),
    especialidade: str = typer.Argument(..., help="Especialidade medica, ex: dermatologia"),
    output: Path = typer.Option(
        Path("outputs"), "--output", "-o", help="Diretorio onde salvar JSON, MD e HTML."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs detalhados."),
    abrir_html: bool = typer.Option(
        False, "--abrir-html", help="Abre o HTML gerado no navegador padrao."
    ),
    n_max: Optional[int] = typer.Option(
        None, "--top", help="Numero maximo de referencias na saida (override do .env)."
    ),
    demo: bool = typer.Option(
        False,
        "--demo",
        help=(
            "Roda em modo DEMO: usa fixtures sinteticas em vez de scraping real. "
            "Util para avaliar a logica em rede que bloqueia Meta. Veja docs/TRADE_OFFS.md."
        ),
    ),
) -> None:
    """Roda o pipeline completo de busca."""

    import os

    if verbose:
        os.environ["VAIPRI_VERBOSE"] = "true"
    if n_max is not None:
        os.environ["VAIPRI_TOP_N"] = str(n_max)

    cfg = carregar()
    if cfg.chave_anthropic_parece_placeholder:
        console.print(
            "[yellow]>> Sua ANTHROPIC_API_KEY parece um placeholder do .env.example "
            "(contem 'xxx' ou e muito curta).\n"
            "   A ferramenta vai rodar em modo heuristico (sem Claude) "
            "— isso e suficiente para o modo --demo.\n"
            "   Se quiser ativar o Claude, edite o .env ou apague o arquivo.[/]"
        )
    elif not cfg.tem_chave_anthropic:
        console.print(
            "[yellow]>> ANTHROPIC_API_KEY nao detectada. A ferramenta vai rodar em modo "
            "heuristico (sem Claude). Configure o .env para qualidade maxima.[/]"
        )

    # Aviso sobre fonte de dados (Graph API vs scraping vs demo).
    if not demo and not cfg.tem_meta_token:
        console.print(
            "[yellow]>> Modo PRODUCAO sem META_ACCESS_TOKEN configurado.\n"
            "   Vou tentar scraping da UI publica, mas a Meta bloqueia esse caminho "
            "em quase todas as redes.\n"
            "   Recomendado: configure o token (gratuito, 5 min) — ver "
            "docs/COMO_ATIVAR_DADOS_REAIS.md\n"
            "   Alternativa: rode com --demo para validar pipeline com fixtures.[/]"
        )
    elif not demo and cfg.tem_meta_token:
        console.print(
            "[green]>> Modo PRODUCAO com Graph API oficial (META_ACCESS_TOKEN OK).[/]"
        )

    estado = {"etapa": "iniciando", "candidato": 0, "total": 0, "fb_page": ""}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        tarefa = progress.add_task("preparando", total=100)

        def on_progress(etapa: str, info: dict) -> None:
            estado["etapa"] = etapa
            if etapa == "inicio":
                progress.update(tarefa, description="iniciando", completed=2)
            elif etapa == "termos":
                progress.update(tarefa, description="gerando termos de busca", completed=10)
            elif etapa == "ad_library":
                progress.update(tarefa, description="consultando Meta Ad Library", completed=25)
            elif etapa == "candidato":
                total = info.get("total", 1) or 1
                i = info.get("i", 0)
                pct = 30 + int(60 * (i / total))
                progress.update(
                    tarefa,
                    description=f"enriquecendo candidato {i}/{total}: {info.get('fb_page_name','?')[:40]}",
                    completed=pct,
                )
            elif etapa == "fim":
                progress.update(tarefa, description="finalizando", completed=98)

        try:
            resultado = buscar_referencias(
                handle_cliente=handle,
                especialidade=especialidade,
                config=cfg,
                on_progress=on_progress,
                modo_demo=demo,
            )
        except Exception as exc:
            console.print(f"[red]erro fatal:[/] {exc}")
            raise typer.Exit(code=1) from exc

        progress.update(tarefa, completed=100, description="pronto")

    paths = salvar(resultado, diretorio=output)
    _imprimir_sumario(resultado, paths)

    if abrir_html:
        import webbrowser

        webbrowser.open(paths["html"].resolve().as_uri())


def _imprimir_sumario(res, paths) -> None:
    """Tabela com as referencias e paths gerados."""
    if res.avisos:
        console.print(
            Panel(
                "\n".join(f"- {a}" for a in res.avisos),
                title="[yellow]Avisos do pipeline[/]",
                border_style="yellow",
            )
        )

    if res.lista_incompleta and res.justificativa_lista_incompleta:
        console.print(
            Panel(
                res.justificativa_lista_incompleta,
                title="[red]Lista incompleta[/]",
                border_style="red",
            )
        )

    table = Table(title=f"Referencias — {res.especialidade.title()} (Top {len(res.referencias)})")
    table.add_column("#", style="bold")
    table.add_column("Instagram", style="cyan")
    table.add_column("Nome")
    table.add_column("Ads", justify="right")
    table.add_column("Seguidores", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Match", justify="right")

    for i, ref in enumerate(res.referencias, start=1):
        table.add_row(
            str(i),
            f"@{ref.instagram_handle}",
            (ref.nome_exibicao or "")[:32],
            str(ref.n_anuncios_ativos),
            _fmt_int(ref.metricas.seguidores),
            f"{ref.score:.0f}",
            f"{int(ref.especialidade_confianca * 100)}%",
        )

    console.print(table)

    console.print(
        Panel(
            "\n".join(
                [
                    f"JSON   : {paths['json']}",
                    f"Markdown: {paths['md']}",
                    f"HTML    : {paths['html']}",
                ]
            ),
            title="[green]Saidas geradas[/]",
            border_style="green",
        )
    )


def _fmt_int(v):
    if v is None:
        return "n/d"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M".replace(".0M", "M")
    if v >= 1_000:
        return f"{v/1_000:.1f}k".replace(".0k", "k")
    return str(v)


@app.command()
def versao() -> None:
    """Mostra a versao."""
    from vaipri_ref import __version__

    console.print(f"vaipri-ref versao {__version__}")


if __name__ == "__main__":  # pragma: no cover
    app()
