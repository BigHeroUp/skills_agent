"""Minimal in-memory state for the Veraxis kernel."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class KernelMemory:
    """Ephemeral in-memory storage for kernel runtime state."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._store)
