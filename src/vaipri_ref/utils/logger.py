"""Logger compartilhado, com saida Rich quando disponivel."""

from __future__ import annotations

import logging
import sys

try:
    from rich.console import Console
    from rich.logging import RichHandler

    _CONSOLE = Console(stderr=True)
    _RICH = True
except Exception:  # pragma: no cover
    _CONSOLE = None  # type: ignore[assignment]
    _RICH = False


def configurar(verbose: bool = False) -> logging.Logger:
    """Configura o logger raiz do pacote."""
    level = logging.DEBUG if verbose else logging.INFO

    logger = logging.getLogger("vaipri_ref")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    if _RICH:
        handler: logging.Handler = RichHandler(
            console=_CONSOLE,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:  # pragma: no cover
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))

    handler.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def obter() -> logging.Logger:
    return logging.getLogger("vaipri_ref")
