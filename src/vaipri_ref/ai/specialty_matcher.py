"""Classificador de especialidade medica usando Claude.

Recebe bio/nome/url do candidato + especialidade alvo e retorna
(match, confianca, justificativa).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vaipri_ref.ai.claude_client import ClaudeClient
from vaipri_ref.utils.logger import obter as obter_logger

logger = obter_logger()


# Palavras-chave que servem como fallback heuristico quando o Claude
# nao esta disponivel. Cobre as ~15 especialidades mais comuns no Brasil.
_HEURISTICAS_FALLBACK: dict[str, list[str]] = {
    "dermatologia": [
        "dermato", "dermatologia", "dermatologista", "pele", "acne",
        "melasma", "botox", "preenchimento", "harmonizacao",
    ],
    "nutrologia": [
        "nutrologia", "nutrologo", "nutrologa", "nutricao", "emagrecimento",
        "obesidade", "metabolico", "metabolismo",
    ],
    "ortopedia": [
        "ortopedia", "ortopedista", "joelho", "coluna", "ombro",
        "quadril", "traumato", "lesao",
    ],
    "ginecologia": [
        "ginecologia", "ginecologista", "obstetricia", "obstetra", "gineco",
    ],
    "cardiologia": [
        "cardiologia", "cardiologista", "cardio", "coracao",
    ],
    "psiquiatria": [
        "psiquiatra", "psiquiatria", "saude mental", "ansiedade", "depressao",
    ],
    "oftalmologia": [
        "oftalmologia", "oftalmologista", "oftalmo", "olhos", "visao",
    ],
    "endocrinologia": [
        "endocrino", "endocrinologia", "endocrinologista", "diabetes",
        "tireoide", "hormonio",
    ],
    "pediatria": [
        "pediatria", "pediatra", "infantil", "crianca", "neonatal",
    ],
    "urologia": [
        "urologia", "urologista", "rim", "bexiga", "prostata",
    ],
    "otorrinolaringologia": [
        "otorrino", "otorrinolaringologia", "audicao", "rouquidao",
    ],
    "neurologia": [
        "neurologia", "neurologista", "neuro", "cerebro", "enxaqueca",
    ],
    "odontologia": [
        "odonto", "odontologia", "dentista", "dental", "sorriso", "implante",
    ],
    "cirurgia plastica": [
        "cirurgia plastica", "cirurgiao plastico", "plastica", "rinoplastia",
        "abdominoplastia", "mamoplastia", "lipo",
    ],
    "fisioterapia": [
        "fisioterapia", "fisioterapeuta", "fisio", "reabilitacao",
    ],
}


@dataclass
class ResultadoMatch:
    match: bool
    confianca: float  # 0..1
    justificativa: str


class SpecialtyMatcher:
    def __init__(self, claude: ClaudeClient) -> None:
        self.claude = claude

    def avaliar(
        self,
        *,
        especialidade: str,
        nome: str | None,
        bio: str | None,
        nome_fb_page: str | None,
    ) -> ResultadoMatch:
        """Classifica se o perfil corresponde a especialidade dada."""

        contexto_textual = "\n".join(
            f"{rotulo}: {valor!r}"
            for rotulo, valor in [
                ("nome_perfil", nome),
                ("bio", bio),
                ("nome_facebook_page", nome_fb_page),
            ]
            if valor
        )
        if not contexto_textual.strip():
            return ResultadoMatch(
                match=False,
                confianca=0.0,
                justificativa="Sem texto disponivel para avaliar especialidade.",
            )

        # Caminho preferido: Claude.
        if self.claude.disponivel:
            return self._avaliar_claude(especialidade, contexto_textual)

        # Fallback: heuristica de palavras-chave.
        return self._avaliar_heuristica(especialidade, contexto_textual)

    def _avaliar_claude(self, especialidade: str, contexto: str) -> ResultadoMatch:
        prompt = f"""Voce classifica perfis medicos por especialidade. \
Recebe pedacos de texto de um perfil (bio, nome no Instagram, nome da Pagina no Facebook) e \
decide se esse perfil ATUA primariamente na especialidade alvo.

Regras:
- "match" so e true se a especialidade do perfil for a mesma ou um subnicho direto da alvo.
- Subnicho conta: "harmonizacao facial" e dermatologia/medicina estetica → conta como dermatologia.
- Multiplas especialidades em clinica geral: match SOMENTE se a alvo aparecer explicitamente.
- Coach, influencer fitness, marca de produto: NAO e referencia. match = false.
- Hospital / rede de clinicas multi-especialidade: match = false (criativo institucional nao serve).

Especialidade alvo: {especialidade!r}

Trechos do perfil:
{contexto}

Responda APENAS em JSON, com este schema:
{{
  "match": boolean,
  "confianca": numero entre 0 e 1,
  "justificativa": "1-2 frases curtas em pt-BR"
}}
"""
        resposta = self.claude.json_objeto(prompt, max_tokens=300, temperature=0.0)
        if not resposta:
            logger.debug("Claude nao retornou JSON valido, caindo no fallback")
            return self._avaliar_heuristica(especialidade, contexto)

        try:
            match = bool(resposta.get("match", False))
            confianca = float(resposta.get("confianca", 0.0))
            confianca = max(0.0, min(1.0, confianca))
            justif = str(resposta.get("justificativa", "")).strip() or "Sem justificativa."
            return ResultadoMatch(match=match, confianca=confianca, justificativa=justif)
        except (TypeError, ValueError):
            return self._avaliar_heuristica(especialidade, contexto)

    def _avaliar_heuristica(self, especialidade: str, contexto: str) -> ResultadoMatch:
        especialidade_norm = _norm(especialidade)
        palavras = _HEURISTICAS_FALLBACK.get(especialidade_norm, [especialidade_norm])
        contexto_norm = _norm(contexto)

        # Anti-keywords: termos que indicam que NAO e um medico individual
        # e portanto nao serve de referencia (criativo institucional ou
        # nao-medico). Casa com a regra do prompt Claude.
        excluir = [
            "hospital", "rede de clinicas", "plano de saude", "sus",
            "marca de", "loja de", "suplemento",
            "personal trainer", "coach", "influencer", "lifestyle",
            "sem medico", "nao sou medic",  # auto-declaracao
        ]
        for ex in excluir:
            if ex in contexto_norm:
                return ResultadoMatch(
                    match=False,
                    confianca=0.7,
                    justificativa=f"Fallback heuristico: contem {ex!r} (nao serve de referencia de trafego).",
                )

        bate = sum(1 for p in palavras if p in contexto_norm)
        if bate >= 1:
            confianca = min(0.6 + 0.1 * bate, 0.9)
            return ResultadoMatch(
                match=True,
                confianca=confianca,
                justificativa=f"Fallback heuristico: {bate} termos de {especialidade_norm!r} encontrados.",
            )
        return ResultadoMatch(
            match=False,
            confianca=0.3,
            justificativa=f"Fallback heuristico: nenhum termo de {especialidade_norm!r} no texto.",
        )


def _norm(s: str) -> str:
    import unicodedata

    s = s.lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s)
    return s
