"""Bounded concurrency guard for integrated local product flows."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path


class ProductFlowBusy(RuntimeError):
    pass


_REGISTRY_LOCK = threading.Lock()
_RESOURCE_LOCKS: dict[str, threading.Lock] = {}


def _lock_for(path: str | Path) -> threading.Lock:
    key = str(Path(path).resolve())
    with _REGISTRY_LOCK:
        return _RESOURCE_LOCKS.setdefault(key, threading.Lock())


@contextmanager
def product_flow_guard(path: str | Path, *, timeout_seconds: float):
    lock = _lock_for(path)
    acquired = lock.acquire(timeout=timeout_seconds)
    if not acquired:
        raise ProductFlowBusy(
            f"Product Intelligence is already running for {Path(path).name}"
        )
    try:
        yield
    finally:
        lock.release()
