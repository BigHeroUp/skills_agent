"""Explicit dry-run repair contracts; no implicit repair rules are registered."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from services.knowledge_graph.domain import GraphFingerprint
from services.knowledge_graph.validation.reader import RawGraphDocumentReader

from .persistence import GraphPersistencePort, GraphWriteReceipt


RepairTransform = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class GraphRepair:
    repair_id: str
    description: str
    transform: RepairTransform


@dataclass(frozen=True)
class RepairPlan:
    source_fingerprint: GraphFingerprint
    repair_ids: tuple[str, ...]
    transformed_document: Mapping[str, Any]
    output_bytes: bytes

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transformed_document",
            MappingProxyType(dict(self.transformed_document)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": True,
            "repair_ids": list(self.repair_ids),
            "source_fingerprint": self.source_fingerprint.to_dict(),
            "output_fingerprint": GraphFingerprint.from_bytes(self.output_bytes).to_dict(),
        }


class GraphRepairService:
    def plan(self, path: str | Path, repairs: tuple[GraphRepair, ...]) -> RepairPlan:
        if not repairs:
            raise ValueError("at least one explicit repair is required")
        if any(not repair.repair_id.strip() for repair in repairs):
            raise ValueError("repair_id must be non-empty")
        if len({repair.repair_id for repair in repairs}) != len(repairs):
            raise ValueError("repair ids must be unique")
        document = RawGraphDocumentReader().read(path)
        if document.fingerprint is None or not isinstance(document.root, Mapping):
            raise ValueError(f"graph is not repair-ready: {document.status.value}")
        transformed: Mapping[str, Any] = dict(document.root)
        for repair in repairs:
            transformed = dict(repair.transform(transformed))
        output = json.dumps(
            transformed,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        return RepairPlan(
            source_fingerprint=document.fingerprint,
            repair_ids=tuple(item.repair_id for item in repairs),
            transformed_document=transformed,
            output_bytes=output,
        )

    def execute(
        self,
        plan: RepairPlan,
        persistence: GraphPersistencePort,
        *,
        confirm_write: bool = False,
        create_backup: bool = False,
    ) -> GraphWriteReceipt:
        if not confirm_write:
            raise ValueError("repair execution requires confirm_write=True")
        return persistence.guarded_write(
            plan.output_bytes,
            expected_fingerprint=plan.source_fingerprint,
            create_backup=create_backup,
        )
