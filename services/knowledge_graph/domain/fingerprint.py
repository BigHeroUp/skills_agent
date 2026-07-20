"""Stable fingerprints for raw Knowledge Graph documents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphFingerprint:
    """SHA-256 fingerprint over the exact raw bytes of a document."""

    value: str
    algorithm: str = "sha256"
    scope: str = "raw"

    @classmethod
    def from_bytes(cls, payload: bytes) -> "GraphFingerprint":
        return cls(value=hashlib.sha256(payload).hexdigest())

    def to_dict(self) -> dict[str, str]:
        return {
            "algorithm": self.algorithm,
            "scope": self.scope,
            "value": self.value,
        }
