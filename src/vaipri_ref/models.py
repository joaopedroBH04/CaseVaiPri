"""Modelos Pydantic para o contrato de saida.

O contrato e estavel: integradores podem confiar nos campos abaixo.
Campos opcionais sao explicitos como `None`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Metricas(BaseModel):
    """Metricas publicas do Instagram do anunciante."""

    model_config = ConfigDict(extra="forbid")

    seguidores: int | None = Field(None, description="Numero de seguidores no IG. None se indisponivel.")
    seguindo: int | None = Field(None, description="Numero de contas seguidas pelo perfil.")
    total_posts: int | None = Field(None, description="Total de posts publicados pelo perfil.")
    engajamento_estimado_percent: float | None = Field(
        None,
        description="Taxa de engajamento estimada (0-100). None se nao foi possivel calcular.",
    )
    posts_ultimos_30_dias: int | None = Field(
        None, description="Quantidade de posts publicados nos ultimos 30 dias."
    )
    bio: str | None = Field(None, description="Bio publica do Instagram, se disponivel.")
    nome_completo: str | None = Field(None, description="Nome publico no perfil do IG.")
    foto_url: HttpUrl | None = Field(None, description="URL da foto de perfil.")
    metricas_completas: bool = Field(
        False,
        description="True se todas as metricas foram obtidas. False se alguma e estimativa ou faltou.",
    )


class Anuncio(BaseModel):
    """Sumario de um anuncio individual encontrado na Ad Library."""

    model_config = ConfigDict(extra="forbid")

    ad_archive_id: str | None = None
    formato: Literal["video", "imagem", "carrossel", "desconhecido"] = "desconhecido"
    comecou_em: datetime | None = None
    preview_url: HttpUrl | None = None


class Candidato(BaseModel):
    """Resultado bruto da Ad Library antes do enriquecimento."""

    model_config = ConfigDict(extra="forbid")

    fb_page_id: str
    fb_page_name: str
    fb_page_url: HttpUrl | None = None
    n_anuncios_ativos: int = 0
    instagram_handle_hint: str | None = None
    termo_busca_origem: str | None = None


class Referencia(BaseModel):
    """Item final de saida: uma referencia validada de medico."""

    model_config = ConfigDict(extra="forbid")

    # Identificacao
    instagram_handle: str | None = Field(
        None,
        description=(
            "Handle do IG sem @, ex: 'dra.fulana'. None quando nao foi possivel "
            "resolver automaticamente — nesse caso use fb_page_name + biblioteca_anuncios_url "
            "para localizar manualmente."
        ),
    )
    instagram_url: HttpUrl | None = Field(
        None, description="URL do perfil IG. None quando handle nao foi resolvido."
    )
    nome_exibicao: str | None = None

    # Anuncios
    fb_page_id: str
    fb_page_name: str
    n_anuncios_ativos: int
    biblioteca_anuncios_url: HttpUrl = Field(
        ..., description="Link direto pros anuncios desse anunciante na Ad Library."
    )
    confirmacao_anuncio_ativo: bool = Field(
        ..., description="True quando ha pelo menos 1 anuncio ativo agora."
    )

    # Metricas
    metricas: Metricas

    # Especialidade
    especialidade_alvo: str
    especialidade_match: bool
    especialidade_confianca: float = Field(
        ..., ge=0.0, le=1.0, description="Confianca de 0 a 1 do match de especialidade."
    )
    especialidade_justificativa: str | None = None

    # Score extra
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Nota 0 (ruim) a 10 (excelente) — soma das parcelas em score_breakdown.",
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Composicao do score por criterio, com nomes em portugues. "
            "Cada valor e quanto aquela parcela contribuiu, em escala 0-peso."
        ),
    )
    score_rotulo: str = Field(
        default="",
        description="Rotulo humano: Excelente / Muito boa / Boa / Razoavel / Fraca.",
    )

    # Procedencia
    confianca_handle: Literal["alta", "media", "baixa"] = "media"
    notas: list[str] = Field(default_factory=list, description="Observacoes do pipeline.")


class Resultado(BaseModel):
    """Envelope completo da saida da ferramenta."""

    model_config = ConfigDict(extra="forbid")

    handle_cliente: str
    especialidade: str
    pais: str
    gerado_em: datetime

    referencias: list[Referencia]

    # Meta
    n_candidatos_brutos: int = 0
    n_filtrados_por_especialidade: int = 0
    n_descartados_sem_anuncio: int = 0
    termos_busca_usados: list[str] = Field(default_factory=list)

    # Quando a lista vem com menos de N (TOP_N) itens
    lista_incompleta: bool = False
    justificativa_lista_incompleta: str | None = None

    # Trade-offs declarados em runtime
    avisos: list[str] = Field(default_factory=list)

    def como_json(self) -> str:
        return self.model_dump_json(indent=2)
