"""Configuracao carregada do .env com defaults sensatos."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_DEFAULT_COUNTRY = "BR"
_DEFAULT_MAX_CANDIDATOS = 40
_DEFAULT_TOP_N = 10
_DEFAULT_CACHE_DIR = ".cache"


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

    @property
    def tem_chave_anthropic(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.startswith("sk-"))


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
    )
