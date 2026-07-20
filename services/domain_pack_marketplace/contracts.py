"""Offline Domain Pack marketplace contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class PackLifecycleStatus(str, Enum):
    INSTALLED = "installed"
    INVALID = "invalid"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class PackCompatibility:
    compatible: bool
    reasons: tuple[str, ...]
    platform_version: str
    graph_schema_version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "graph_schema_version": self.graph_schema_version,
            "platform_version": self.platform_version,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class MarketplaceEntry:
    pack_id: str
    name: str
    version: str
    status: PackLifecycleStatus
    path: Path
    compatibility: PackCompatibility
    validation_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatibility": self.compatibility.to_dict(),
            "name": self.name,
            "pack_id": self.pack_id,
            "path": str(self.path),
            "status": self.status.value,
            "validation_errors": list(self.validation_errors),
            "version": self.version,
        }


@dataclass(frozen=True)
class BundleReceipt:
    pack_id: str
    version: str
    bundle_path: Path
    checksum: str
    file_count: int


@dataclass(frozen=True)
class InstallReceipt:
    pack_id: str
    version: str
    installed_path: Path
    bundle_checksum: str
