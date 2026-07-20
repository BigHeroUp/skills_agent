"""Persistence ports and guarded filesystem writes for graph lifecycle operations."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from services.knowledge_graph.domain import GraphFingerprint


class ConcurrentGraphChange(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphWriteReceipt:
    path: Path
    backup_path: Path
    previous_fingerprint: GraphFingerprint
    current_fingerprint: GraphFingerprint


class GraphPersistencePort(Protocol):
    @property
    def path(self) -> Path: ...

    def read_bytes(self) -> bytes: ...

    def guarded_write(
        self,
        payload: bytes,
        *,
        expected_fingerprint: GraphFingerprint,
        create_backup: bool,
    ) -> GraphWriteReceipt: ...


class FilesystemGraphPersistence:
    """Atomic writer that requires optimistic locking and an explicit backup."""

    def __init__(self, path: str | Path):
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()

    def guarded_write(
        self,
        payload: bytes,
        *,
        expected_fingerprint: GraphFingerprint,
        create_backup: bool,
    ) -> GraphWriteReceipt:
        if not create_backup:
            raise ValueError("lifecycle writes require create_backup=True")
        current = self.read_bytes()
        current_fingerprint = GraphFingerprint.from_bytes(current)
        if current_fingerprint != expected_fingerprint:
            raise ConcurrentGraphChange(
                "Knowledge Graph changed after the lifecycle plan was created"
            )

        backup_path = self.path.with_name(
            f"{self.path.name}.bak-{current_fingerprint.value[:12]}"
        )
        if backup_path.exists() and backup_path.read_bytes() != current:
            raise FileExistsError(f"backup collision: {backup_path}")
        backup_path.write_bytes(current)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return GraphWriteReceipt(
            path=self.path,
            backup_path=backup_path,
            previous_fingerprint=current_fingerprint,
            current_fingerprint=GraphFingerprint.from_bytes(payload),
        )
