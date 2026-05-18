"""Gerador de termos de busca para a Ad Library.

Dado "dermatologia", gera termos em pt-BR que provavelmente aparecerao
em anuncios reais de dermatologistas no Brasil. Vai alem da palavra-raiz:
inclui procedimentos, sinonimos populares e variacoes que clinicas usam
em copy de anuncio.
"""

from __future__ import annotations

from vaipri_ref.ai.claude_client import ClaudeClient
from vaipri_ref.utils.logger import obter as obter_logger

logger = obter_logger()


# Dicionario curado por especialidade comum. Serve como fallback (sem IA)
# e tambem como "alimento" para o prompt do Claude, garantindo qualidade.
_TERMOS_BASE: dict[str, list[str]] = {
    "dermatologia": [
        "dermatologista", "dermato", "harmonizacao facial", "botox",
        "preenchimento labial", "tratamento de pele", "melasma",
        "acne", "limpeza de pele", "clinica de estetica medica",
    ],
    "nutrologia": [
        "nutrologo", "nutrologa", "emagrecimento", "obesidade", "perda de peso",
        "ozempic", "tratamento metabolico", "consultoria nutricional medica",
        "saude metabolica", "reposicao hormonal",
    ],
    "ortopedia": [
        "ortopedista", "ortopedia", "dor no joelho", "dor nas costas",
        "hernia de disco", "lesao no ombro", "fisiatria",
        "infiltracao", "cirurgia de joelho", "traumatologia",
    ],
    "ginecologia": [
        "ginecologista", "ginecologia", "obstetra", "obstetricia",
        "pre-natal", "endometriose", "miomas", "reposicao hormonal feminina",
        "ginecologia regenerativa",
    ],
    "cardiologia": [
        "cardiologista", "cardiologia", "check up cardiologico",
        "arritmia", "hipertensao", "coracao saudavel", "ecocardiograma",
    ],
    "psiquiatria": [
        "psiquiatra", "ansiedade", "depressao", "transtorno bipolar",
        "burnout", "saude mental", "psicofarmaco",
    ],
    "odontologia": [
        "implante dentario", "lente de contato dental", "clareamento",
        "ortodontia", "harmonizacao orofacial", "dentista",
        "clinica odontologica",
    ],
    "cirurgia plastica": [
        "cirurgia plastica", "cirurgiao plastico", "rinoplastia",
        "lipo HD", "abdominoplastia", "mamoplastia", "mommy makeover",
        "lipoaspiracao",
    ],
}


_PROMPT_SISTEMA = """Voce gera consultas de busca para a Biblioteca de Anuncios da Meta.
Objetivo: encontrar anuncios reais de medicos brasileiros de uma especialidade especifica.

Regras:
- Idioma: pt-BR exclusivamente.
- Sem acento. Sem palavras genericas demais como "saude" ou "medico".
- Inclua: nome formal da especialidade, sinonimos, procedimentos campeoes
  de venda, dores que o paciente sente e busca tratamento.
- Excluir: termos institucionais (hospital, plano de saude, SUS) e
  termos de outras especialidades.
- Itens devem ser strings simples (sem aspas, sem operadores booleanos).
- Saida: JSON array com EXATAMENTE 10 itens, ordenado do mais especifico ao mais amplo.
"""


def gerar_termos(
    especialidade: str,
    *,
    claude: ClaudeClient,
    n: int = 10,
) -> list[str]:
    """Gera termos de busca para a especialidade. Mistura curadoria + Claude."""

    chave = especialidade.strip().lower()
    base = _TERMOS_BASE.get(chave, [chave])

    if not claude.disponivel:
        logger.info("Claude indisponivel; usando termos curados para %s", chave)
        return base[:n] if len(base) >= n else _ampliar_simples(base, n)

    prompt = (
        f"Especialidade alvo: {especialidade!r}.\n\n"
        f"Termos de seed (uso interno, voce pode reaproveitar): {base}.\n\n"
        f"Gere {n} termos seguindo as regras do sistema. JSON array de strings."
    )

    resposta = claude.json_lista(
        prompt,
        sistema=_PROMPT_SISTEMA,
        max_tokens=400,
        temperature=0.2,
    )

    if resposta is None:
        logger.info("Claude nao retornou JSON; usando termos curados para %s", chave)
        return base[:n] if len(base) >= n else _ampliar_simples(base, n)

    termos = [str(t).strip() for t in resposta if isinstance(t, (str, int))]
    termos = [t for t in termos if t]
    termos = list(dict.fromkeys(termos))  # dedup mantendo ordem
    if len(termos) < n:
        # complementa com base
        for t in base:
            if t not in termos:
                termos.append(t)
            if len(termos) >= n:
                break
    return termos[:n]


def _ampliar_simples(base: list[str], n: int) -> list[str]:
    """Quando ha menos termos curados que o desejado, cria variacoes simples."""
    out: list[str] = list(base)
    variantes = ["clinica", "consultorio", "tratamento", "dr", "dra"]
    for var in variantes:
        for b in base:
            candidato = f"{var} {b}".strip()
            if candidato not in out:
                out.append(candidato)
            if len(out) >= n:
                return out[:n]
    return out[:n]
