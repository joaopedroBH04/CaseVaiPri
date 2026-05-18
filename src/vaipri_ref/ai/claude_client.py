"""Wrapper fino sobre o SDK da Anthropic.

Centraliza:
- retry com backoff em rate limit / timeout
- parsing tolerante de JSON na resposta
- modo offline quando a chave nao esta configurada (retorna None)
"""

from __future__ import annotations

import json
import re
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from vaipri_ref.utils.logger import obter as obter_logger

logger = obter_logger()

try:
    import anthropic
    from anthropic import APIError, APITimeoutError, RateLimitError

    _SDK_DISPONIVEL = True
    _ERROS_RETRY = (RateLimitError, APITimeoutError, APIError)
except Exception:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    _SDK_DISPONIVEL = False
    _ERROS_RETRY = ()  # type: ignore[assignment]


class ClaudeClient:
    """Cliente Claude com modo degradado quando nao ha chave."""

    def __init__(self, api_key: str | None, model: str) -> None:
        self.model = model
        self.api_key = api_key
        self._client = None
        if _SDK_DISPONIVEL and api_key and api_key.startswith("sk-"):
            self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def disponivel(self) -> bool:
        return self._client is not None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(_ERROS_RETRY) if _ERROS_RETRY else retry_if_exception_type(Exception),
        reraise=True,
    )
    def texto(
        self,
        prompt: str,
        *,
        sistema: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str | None:
        """Retorna texto livre. None quando nao ha cliente."""
        if not self._client:
            return None

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if sistema:
            kwargs["system"] = sistema

        try:
            resp = self._client.messages.create(**kwargs)
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        except Exception as exc:
            logger.warning(f"Claude falhou: {exc}")
            raise

    def json_objeto(
        self,
        prompt: str,
        *,
        sistema: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any] | None:
        """Tenta extrair um objeto JSON da resposta. None em falha."""
        resposta = self.texto(prompt, sistema=sistema, max_tokens=max_tokens, temperature=temperature)
        if resposta is None:
            return None
        return _extrair_json_objeto(resposta)

    def json_lista(
        self,
        prompt: str,
        *,
        sistema: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> list[Any] | None:
        """Tenta extrair uma lista JSON da resposta. None em falha."""
        resposta = self.texto(prompt, sistema=sistema, max_tokens=max_tokens, temperature=temperature)
        if resposta is None:
            return None
        return _extrair_json_lista(resposta)


# ---------- parsing tolerante ----------


_JSON_BLOCO = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _limpar_bloco(texto: str) -> str:
    match = _JSON_BLOCO.search(texto)
    if match:
        return match.group(1).strip()
    return texto.strip()


def _extrair_json_objeto(texto: str) -> dict[str, Any] | None:
    candidato = _limpar_bloco(texto)
    try:
        valor = json.loads(candidato)
        if isinstance(valor, dict):
            return valor
    except json.JSONDecodeError:
        pass

    primeiro = candidato.find("{")
    ultimo = candidato.rfind("}")
    if primeiro != -1 and ultimo != -1 and ultimo > primeiro:
        try:
            valor = json.loads(candidato[primeiro : ultimo + 1])
            if isinstance(valor, dict):
                return valor
        except json.JSONDecodeError:
            return None
    return None


def _extrair_json_lista(texto: str) -> list[Any] | None:
    candidato = _limpar_bloco(texto)
    try:
        valor = json.loads(candidato)
        if isinstance(valor, list):
            return valor
    except json.JSONDecodeError:
        pass

    primeiro = candidato.find("[")
    ultimo = candidato.rfind("]")
    if primeiro != -1 and ultimo != -1 and ultimo > primeiro:
        try:
            valor = json.loads(candidato[primeiro : ultimo + 1])
            if isinstance(valor, list):
                return valor
        except json.JSONDecodeError:
            return None
    return None
