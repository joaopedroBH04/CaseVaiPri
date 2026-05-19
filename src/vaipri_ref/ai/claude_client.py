"""Wrapper fino sobre o SDK da Anthropic.

Centraliza:
- retry com backoff em rate limit / timeout
- parsing tolerante de JSON na resposta
- modo offline quando a chave nao esta configurada (retorna None)
- modo degradado quando a chave existe mas e invalida/sem credito:
  detectamos o erro fatal, desabilitamos o cliente e seguimos no
  fallback heuristico sem explodir o pipeline.
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
    from anthropic import (
        APIError,
        APITimeoutError,
        RateLimitError,
    )

    # Erros transitorios — vale a pena retry com backoff.
    _ERROS_RETRY: tuple = (RateLimitError, APITimeoutError)

    # Erros FATAIS — chave invalida, sem credito, modelo nao existe.
    # NAO retry: re-tentar e jogar dinheiro fora e atrasar o pipeline.
    # Captura por status quando o SDK nao expoe subclasse especifica.
    _ERROS_FATAIS_NOMES = {
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "BadRequestError",
    }

    _SDK_DISPONIVEL = True
except Exception:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    APIError = APITimeoutError = RateLimitError = Exception  # type: ignore[assignment,misc]
    _ERROS_RETRY = ()
    _ERROS_FATAIS_NOMES = set()
    _SDK_DISPONIVEL = False


def _erro_fatal(exc: BaseException) -> bool:
    """Retorna True para erros que NAO devem ser re-tentados nem propagados."""
    nome = type(exc).__name__
    if nome in _ERROS_FATAIS_NOMES:
        return True
    # Fallback por status HTTP, caso o SDK serialize diferente.
    status = getattr(exc, "status_code", None)
    return status in (400, 401, 403, 404)


class ClaudeClient:
    """Cliente Claude com modo degradado quando nao ha chave OU
    quando a chave existe mas e invalida em runtime.
    """

    def __init__(self, api_key: str | None, model: str) -> None:
        # Import local pra evitar dependencia circular config <-> ai.
        from vaipri_ref.config import _chave_parece_real

        self.model = model
        self.api_key = api_key
        self._client = None
        self._aviso_fatal: str | None = None  # mensagem amigavel

        if not _SDK_DISPONIVEL or not api_key:
            return

        if not _chave_parece_real(api_key):
            # Provavelmente placeholder do .env.example. Nao tenta chamar
            # a API — evita 401 desnecessario e mensagens de erro confusas.
            self._aviso_fatal = (
                "ANTHROPIC_API_KEY parece um placeholder (xxxxx, <cole-aqui>, "
                "ou muito curta). Nao chamei a API. Rodando em modo heuristico. "
                "Para ativar o Claude, apague o .env ou cole sua chave real."
            )
            logger.warning(self._aviso_fatal)
            return

        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def disponivel(self) -> bool:
        return self._client is not None

    @property
    def aviso_fatal(self) -> str | None:
        """Mensagem amigavel quando a chave era valida no construtor mas
        provou-se invalida na primeira chamada. None se nao houve."""
        return self._aviso_fatal

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(_ERROS_RETRY) if _ERROS_RETRY else retry_if_exception_type(()),
        reraise=True,
    )
    def _chamar_com_retry(self, kwargs: dict[str, Any]) -> str:
        resp = self._client.messages.create(**kwargs)  # type: ignore[union-attr]
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    def texto(
        self,
        prompt: str,
        *,
        sistema: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str | None:
        """Retorna texto livre. None se cliente indisponivel OU falha fatal."""
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
            return self._chamar_com_retry(kwargs)
        except Exception as exc:
            if _erro_fatal(exc):
                # Desabilita o cliente: nao adianta tentar de novo.
                msg = f"Chave Claude rejeitada pela API ({type(exc).__name__}). Caindo no modo heuristico."
                logger.warning(msg)
                self._client = None
                self._aviso_fatal = msg
                return None
            # Erro transitorio que esgotou retries: melhor logar e cair,
            # nao propagar (o pipeline tem fallback pra None).
            logger.warning(f"Claude falhou apos retries: {exc}")
            return None

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
