"""Score 0-100 (extra escolhido do enunciado).

Formula transparente, documentada em docs/TRADE_OFFS.md. Cada parcela
do score retorna seu valor isolado para que o relatorio possa exibir
o breakdown e o analista possa contestar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class EntradaScore:
    n_anuncios_ativos: int
    seguidores: int | None
    engajamento_percent: float | None
    bio_menciona_especialidade: bool
    posts_ultimos_30_dias: int | None
    confianca_handle: Literal["alta", "media", "baixa"]


def _normalizar(valor: float, piso: float, teto: float) -> float:
    if valor <= piso:
        return 0.0
    if valor >= teto:
        return 1.0
    return (valor - piso) / (teto - piso)


def calcular(entrada: EntradaScore) -> tuple[float, dict[str, float]]:
    """Retorna (score 0-100, breakdown por parcela)."""

    parcelas: dict[str, float] = {}

    parcelas["volume_anuncios"] = 25.0 * _normalizar(entrada.n_anuncios_ativos, piso=1, teto=30)

    if entrada.seguidores is None:
        parcelas["seguidores"] = 0.0
    else:
        parcelas["seguidores"] = 20.0 * _normalizar(entrada.seguidores, piso=1_000, teto=200_000)

    if entrada.engajamento_percent is None:
        parcelas["engajamento"] = 0.0
    else:
        parcelas["engajamento"] = 15.0 if entrada.engajamento_percent >= 1.0 else 0.0

    if entrada.posts_ultimos_30_dias is None:
        parcelas["postagem_recente"] = 7.5  # crédito parcial: nao conseguimos medir
    else:
        parcelas["postagem_recente"] = 15.0 if entrada.posts_ultimos_30_dias >= 1 else 0.0

    parcelas["bio_coerente"] = 15.0 if entrada.bio_menciona_especialidade else 0.0

    handle_w = {"alta": 10.0, "media": 6.0, "baixa": 2.0}[entrada.confianca_handle]
    parcelas["confianca_handle"] = handle_w

    total = round(sum(parcelas.values()), 2)
    total = max(0.0, min(100.0, total))
    return total, parcelas
