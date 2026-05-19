"""Score 0-10 (extra escolhido do enunciado).

Formula transparente com nomes humanos para que qualquer pessoa
entenda por que um medico tirou tal nota — nao so quem tem
conhecimento tecnico.

Escala: 0 (ruim) a 10 (excelente). Cada parcela vira uma "nota
parcial" tambem em escala humana ("forte/medio/fraco" ou pontos).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# Nomes em portugues que aparecem no breakdown publico (CLI, HTML, JSON).
# Pesos somam 10.0 (escala 0-10 do score final).
PESOS = {
    "Volume de anúncios rodando":   2.5,  # antes 25/100
    "Tração no Instagram":          2.0,  # antes 20/100
    "Engajamento real":             1.5,  # antes 15/100
    "Perfil ativo (posts recentes)": 1.5,  # antes 15/100
    "Identidade médica clara":      1.5,  # antes 15/100
    "Confiabilidade do match":      1.0,  # antes 10/100
}


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
    """Retorna (score 0-10, breakdown por parcela em escala 0-peso).

    O breakdown usa chaves em portugues humano. Cada valor e o quanto
    aquela parcela contribuiu pro total (max = peso da parcela).
    """

    parcelas: dict[str, float] = {}

    # 1. Volume de anuncios rodando (max 2.5): mais ads = mais aprendizado
    #    pro time copiar. Piso 1 (precisa pelo menos 1 ativo), teto 30
    #    (acima disso satura).
    parcelas["Volume de anúncios rodando"] = (
        PESOS["Volume de anúncios rodando"]
        * _normalizar(entrada.n_anuncios_ativos, piso=1, teto=30)
    )

    # 2. Tração no Instagram (max 2.0): seguidores. Piso 1k, teto 200k.
    if entrada.seguidores is None:
        parcelas["Tração no Instagram"] = 0.0
    else:
        parcelas["Tração no Instagram"] = (
            PESOS["Tração no Instagram"]
            * _normalizar(entrada.seguidores, piso=1_000, teto=200_000)
        )

    # 3. Engajamento real (max 1.5): taxa >= 1% indica perfil engajado,
    #    nao inflado por seguidores comprados.
    if entrada.engajamento_percent is None:
        parcelas["Engajamento real"] = 0.0
    else:
        parcelas["Engajamento real"] = (
            PESOS["Engajamento real"] if entrada.engajamento_percent >= 1.0 else 0.0
        )

    # 4. Perfil ativo (max 1.5): postou nos ultimos 30 dias.
    if entrada.posts_ultimos_30_dias is None:
        # Credito parcial quando IG nao foi acessivel — nao penalizar
        # perfil possivelmente bom so porque a Meta bloqueou o scrape.
        parcelas["Perfil ativo (posts recentes)"] = PESOS["Perfil ativo (posts recentes)"] / 2
    else:
        parcelas["Perfil ativo (posts recentes)"] = (
            PESOS["Perfil ativo (posts recentes)"]
            if entrada.posts_ultimos_30_dias >= 1
            else 0.0
        )

    # 5. Identidade medica clara (max 1.5): bio menciona especialidade ou CRM.
    parcelas["Identidade médica clara"] = (
        PESOS["Identidade médica clara"] if entrada.bio_menciona_especialidade else 0.0
    )

    # 6. Confiabilidade do match (max 1.0): quao confiante estamos do handle IG.
    confianca_para_pontos = {"alta": 1.0, "media": 0.6, "baixa": 0.2}
    parcelas["Confiabilidade do match"] = (
        PESOS["Confiabilidade do match"] * confianca_para_pontos[entrada.confianca_handle]
    )

    total = round(sum(parcelas.values()), 2)
    total = max(0.0, min(10.0, total))
    return total, parcelas


def rotulo_qualitativo(nota: float) -> str:
    """Traduz a nota 0-10 em rotulo humano que aparece no relatorio."""
    if nota >= 8.5:
        return "Excelente"
    if nota >= 7.0:
        return "Muito boa"
    if nota >= 5.5:
        return "Boa"
    if nota >= 4.0:
        return "Razoável"
    return "Fraca"
