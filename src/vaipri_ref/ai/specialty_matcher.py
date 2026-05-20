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
        termo_busca_origem: str | None = None,
    ) -> ResultadoMatch:
        """Classifica se o perfil corresponde a especialidade dada.

        Args:
            termo_busca_origem: termo da Ad Library que retornou este anunciante.
                Quando bate com termos da especialidade, e' EVIDENCIA FORTE
                de match — a Meta ja filtrou pra nos. Util quando o nome FB
                e' generico (ex: "Dr Joao Silva" sem mencionar dermato).
        """

        # Anti-keywords sempre eliminam, mesmo com termo_busca_origem positivo.
        contexto_full = " ".join(filter(None, [nome, bio, nome_fb_page]))
        contexto_norm = _norm(contexto_full)
        anti_keywords = [
            # Institucionais
            "hospital", "rede de clinicas", "plano de saude", "sus", "operadora",
            # Marcas / lojas / produtos
            "marca de", "loja de", "loja oficial", "perfil oficial da marca",
            "comercio", "ecommerce", "e-commerce", "compre online", "shop",
            "venda online", "produto oficial",
            # Indústria de cosmeticos e farmacos
            "cosmetic", "cosmeticos", "skincare brand", "linha de produtos",
            "drogaria", "farmacia", "drogarias", "drugstore",
            "suplemento", "vitamina marca",
            # Não-médicos (nutricionista e profissao separada — CRN, nao CRM)
            "personal trainer", "coach", "influencer", "lifestyle",
            "nutricionista crn",  # so filtra se diz explicitamente "nutricionista CRN"
            # Auto-declaracoes
            "sem medico", "nao sou medic", "nao tenho crm", "sem crm",
        ]
        for ex in anti_keywords:
            if ex in contexto_norm:
                return ResultadoMatch(
                    match=False,
                    confianca=0.85,
                    justificativa=f"Filtrado: contem {ex!r} (nao e' medico individual).",
                )

        # Padrao de marca / nao-medico: nome todo em CAPS sem Dr/Dra (ex: 'BEYOUNG').
        # So aplica se nao tem evidencia de medico no contexto.
        if nome_fb_page:
            nome_sem_pontuacao = re.sub(r"[^A-Za-z]", "", nome_fb_page)
            if len(nome_sem_pontuacao) >= 5 and nome_sem_pontuacao.isupper():
                ev_medico = any(
                    t in contexto_norm
                    for t in ["dr.", "dra.", " dr ", " dra ", "crm", "rqe", "medic"]
                )
                if not ev_medico:
                    return ResultadoMatch(
                        match=False,
                        confianca=0.80,
                        justificativa=(
                            f"Nome todo em maiusculas ({nome_fb_page!r}) sem evidencia "
                            "de medico individual — perfil de marca."
                        ),
                    )

        # Quando temos seguidores muito altos (>500k) E nenhuma evidencia de
        # medico individual, e' muito provavel ser marca/loja. Esse heuristico
        # foi adicionado depois de SkinCeuticals/Drogaria São Paulo passarem
        # em testes reais.
        # (so e' aplicado quando temos bio do IG = vindo da Apify)
        if bio and len(bio) > 30:
            bio_norm = _norm(bio)
            indicios_marca = [
                "oficial", "linha", "produto", "kit", "compre", "comprar",
                "envio gratis", "frete gratis", "loja", "site oficial",
                "cosmetic", "cosmeticos", "skincare", "perfume",
                "farmacia", "drogaria", "medicamento",
                "redes sociais", "midias sociais",
            ]
            n_indicios = sum(1 for ind in indicios_marca if ind in bio_norm)
            ev_medico_bio = any(
                t in bio_norm for t in ["medico", "medica", "crm", "rqe", "dr.", "dra."]
            )
            if n_indicios >= 2 and not ev_medico_bio:
                return ResultadoMatch(
                    match=False,
                    confianca=0.80,
                    justificativa=(
                        f"Bio com {n_indicios} indicios de marca/loja "
                        "(linha, kit, comprar, etc) e sem mencao a CRM ou medico."
                    ),
                )

        # Se a Ad Library retornou este anunciante para uma busca por termo
        # da especialidade, isso ja e evidencia forte que estamos certos.
        # A confianca varia conforme MULTIPLOS fatores — nao e' fixa em 85% pra todos.
        if termo_busca_origem:
            esp_norm = _norm(especialidade)
            termo_norm = _norm(termo_busca_origem)
            termos_especialidade = _HEURISTICAS_FALLBACK.get(esp_norm, [esp_norm])
            # Procura o termo canonico mais especifico que bate.
            termo_bateu = None
            for canonico in termos_especialidade:
                if canonico in termo_norm or termo_norm in canonico:
                    termo_bateu = canonico
                    break
            if termo_bateu:
                # Base: 70%
                conf = 0.70
                razoes = [
                    f"veio da busca '{termo_busca_origem}' (termo direto de {especialidade})"
                ]
                # +10% se o nome canonico da especialidade aparece NO TEXTO do perfil
                if any(
                    canonico in contexto_norm
                    for canonico in termos_especialidade[:3]  # principais
                ):
                    conf += 0.10
                    razoes.append("nome do perfil cita a especialidade")
                # +8% se bio/nome mencionam CRM, RQE ou doutor(a)
                if any(t in contexto_norm for t in ["crm", "rqe", "dr.", "dra.", " dr ", " dra "]):
                    conf += 0.08
                    razoes.append("perfil indica registro medico (CRM/RQE/Dr.)")
                # -8% se o nome FB foi 'Page XXX...' (info perdida no scraping)
                if (nome_fb_page or "").startswith("Page ") and not (bio or nome):
                    conf -= 0.08
                    razoes.append("nome da pagina nao capturado (penalidade)")
                # +3% por mais um termo da especialidade aparecendo no texto
                bate_extra = sum(
                    1 for c in termos_especialidade if c in contexto_norm
                )
                if bate_extra >= 2:
                    conf += 0.05
                    razoes.append(f"{bate_extra} termos relacionados aparecem")
                conf = max(0.55, min(0.97, conf))
                return ResultadoMatch(
                    match=True,
                    confianca=round(conf, 2),
                    justificativa="; ".join(razoes).capitalize() + ".",
                )

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
