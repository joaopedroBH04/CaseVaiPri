"""Cache em disco simples para nao re-bater fontes externas."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import diskcache


_TTL_DEFAULT = 60 * 60 * 24  # 24h


class Cache:
    def __init__(self, diretorio: Path, ttl: int = _TTL_DEFAULT) -> None:
        diretorio.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(diretorio))
        self._ttl = ttl

    def chave(self, namespace: str, *partes: Any) -> str:
        bruto = namespace + "|" + "|".join(json.dumps(p, sort_keys=True, default=str) for p in partes)
        return namespace + ":" + hashlib.sha1(bruto.encode("utf-8")).hexdigest()[:16]

    def obter_ou_calcular(self, chave: str, calcular: Callable[[], Any]) -> Any:
        if chave in self._cache:
            return self._cache[chave]
        valor = calcular()
        self._cache.set(chave, valor, expire=self._ttl)
        return valor

    async def obter_ou_calcular_async(self, chave: str, calcular: Callable[[], Any]) -> Any:
        if chave in self._cache:
            return self._cache[chave]
        valor = await calcular()
        self._cache.set(chave, valor, expire=self._ttl)
        return valor

    def set(self, chave: str, valor: Any) -> None:
        self._cache.set(chave, valor, expire=self._ttl)

    def get(self, chave: str, default: Any = None) -> Any:
        return self._cache.get(chave, default=default)

    def clear(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self._cache.close()

    # Suporte a context manager: garante close() mesmo com excecao.
    # Critico no Windows, onde diskcache mantem SQLite aberto e impede
    # rmtree do diretorio enquanto o handle nao for liberado.
    def __enter__(self) -> "Cache":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
