"""Configuracao carregada do .env com defaults sensatos."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_COUNTRY = "BR"
_DEFAULT_MAX_CANDIDATOS = 40
_DEFAULT_TOP_N = 10
_DEFAULT_CACHE_DIR = ".cache"


# Padroes que indicam que o valor e um PLACEHOLDER do .env.example,
# nao uma chave real. Chaves Anthropic reais nao tem 'xxx', sao longas
# (>40 chars) e nao contem palavras como 'cole', 'sua', 'aqui'.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"x{4,}", re.IGNORECASE),         # 'xxxx'
    re.compile(r"<[^>]+>"),                       # '<cole-sua-chave>'
    re.compile(r"\b(cole|sua|aqui|exemplo|placeholder)\b", re.IGNORECASE),
]


def _chave_parece_real(key: str | None) -> bool:
    """True se a string parece uma chave Anthropic genuina.

    Genuino: comeca com 'sk-', tem >= 40 chars, nao bate em padrao
    de placeholder. Conservador: ainda pode aceitar chave invalida
    (so a API sabe ao certo), mas filtra os falso-positivos obvios.
    """
    if not key:
        return False
    key = key.strip()
    if not key.startswith("sk-"):
        return False
    if len(key) < 40:
        return False
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.search(key):
            return False
    return True


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    claude_model: str
    country: str
    max_candidatos: int
    top_n: int
    cache_dir: Path
    headless: bool
    verbose: bool
    # Meta Ad Library Graph API (caminho oficial para dados reais)
    meta_access_token: str | None = None
    # Apify (resolve cenarios em que Meta Graph API rejeita ou IG bloqueia)
    apify_api_token: str | None = None
    # Actor IDs Apify (sobrescreviveis via env caso defaults nao existam mais)
    apify_ad_library_actor: str = "curious_coder~facebook-ads-library-scraper"
    apify_ig_actor: str = "apify~instagram-profile-scraper"

    @property
    def tem_chave_anthropic(self) -> bool:
        return _chave_parece_real(self.anthropic_api_key)

    @property
    def chave_anthropic_parece_placeholder(self) -> bool:
        """True quando ha algo configurado mas e claramente placeholder."""
        return bool(self.anthropic_api_key) and not _chave_parece_real(self.anthropic_api_key)

    @property
    def tem_meta_token(self) -> bool:
        """True se ha um token Meta Graph API configurado e nao-placeholder."""
        return _token_parece_real(self.meta_access_token, min_len=20)

    @property
    def tem_apify_token(self) -> bool:
        """True se ha um token Apify configurado e nao-placeholder.

        Aceita tanto o formato 'apify_api_xxx' quanto tokens sem prefixo
        (depende de como o usuario copiou da plataforma Apify).
        """
        if not self.apify_api_token:
            return False
        return _token_parece_real(self.apify_api_token, min_len=20)


def _token_parece_real(t: str | None, *, min_len: int = 20) -> bool:
    if not t:
        return False
    t = t.strip()
    if len(t) < min_len:
        return False
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.search(t):
            return False
    return True


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def carregar(env_file: Path | str | None = None) -> Config:
    """Carrega configuracao do .env (se existir) e variaveis de ambiente."""
    if env_file is None:
        env_file = Path.cwd() / ".env"
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path, override=False)

    return Config(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        claude_model=os.environ.get("VAIPRI_CLAUDE_MODEL", _DEFAULT_MODEL),
        country=os.environ.get("VAIPRI_COUNTRY", _DEFAULT_COUNTRY).upper(),
        max_candidatos=int(os.environ.get("VAIPRI_MAX_CANDIDATOS", _DEFAULT_MAX_CANDIDATOS)),
        top_n=int(os.environ.get("VAIPRI_TOP_N", _DEFAULT_TOP_N)),
        cache_dir=Path(os.environ.get("VAIPRI_CACHE_DIR", _DEFAULT_CACHE_DIR)),
        headless=_bool(os.environ.get("VAIPRI_HEADLESS"), default=True),
        verbose=_bool(os.environ.get("VAIPRI_VERBOSE"), default=False),
        meta_access_token=os.environ.get("META_ACCESS_TOKEN"),
        apify_api_token=os.environ.get("APIFY_API_TOKEN"),
        apify_ad_library_actor=os.environ.get(
            "APIFY_AD_LIBRARY_ACTOR",
            "curious_coder~facebook-ads-library-scraper",
        ),
        apify_ig_actor=os.environ.get(
            "APIFY_IG_ACTOR",
            "apify~instagram-profile-scraper",
        ),
    )
