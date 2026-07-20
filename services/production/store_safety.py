"""Thread-safe atomic JSON persistence helpers for local production stores."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


_REGISTRY_LOCK = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def lock_for_path(path: str | Path) -> threading.RLock:
    key = str(Path(path).resolve())
    with _REGISTRY_LOCK:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def locked_path(path: str | Path) -> Iterator[None]:
    lock = lock_for_path(path)
    with lock:
        yield


def atomic_write_json(path: str | Path, payload: Any, *, max_bytes: int) -> int:
    destination = Path(path)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > max_bytes:
        raise ValueError(
            f"JSON store size {len(encoded)} exceeds configured limit {max_bytes}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return len(encoded)
