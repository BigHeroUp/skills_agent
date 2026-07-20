"""Deterministic migration registry and dry-run-first execution service."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from services.knowledge_graph.domain import GraphFingerprint
from services.knowledge_graph.validation.reader import RawGraphDocumentReader

from .persistence import GraphPersistencePort, GraphWriteReceipt


MigrationTransform = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class GraphMigration:
    migration_id: str
    source_version: int
    target_version: int
    description: str
    transform: MigrationTransform

    def __post_init__(self) -> None:
        if not self.migration_id.strip():
            raise ValueError("migration_id must be non-empty")
        if self.source_version < 1 or self.target_version <= self.source_version:
            raise ValueError("migration versions must move forward")


class MigrationRegistry:
    def __init__(self, migrations: tuple[GraphMigration, ...] = ()):
        self._migrations: dict[tuple[int, int], GraphMigration] = {}
        for migration in migrations:
            self.register(migration)

    def register(self, migration: GraphMigration) -> None:
        key = (migration.source_version, migration.target_version)
        if key in self._migrations:
            raise ValueError(f"duplicate migration path: {key}")
        if any(item.migration_id == migration.migration_id for item in self._migrations.values()):
            raise ValueError(f"duplicate migration id: {migration.migration_id}")
        self._migrations[key] = migration

    def resolve(self, source_version: int, target_version: int) -> tuple[GraphMigration, ...]:
        if target_version < source_version:
            raise ValueError("downgrade migrations are not supported")
        if target_version == source_version:
            return ()
        queue = deque([(source_version, ())])
        visited = {source_version}
        while queue:
            version, path = queue.popleft()
            candidates = sorted(
                (
                    migration for migration in self._migrations.values()
                    if migration.source_version == version
                    and migration.target_version <= target_version
                ),
                key=lambda item: (item.target_version, item.migration_id),
            )
            for migration in candidates:
                next_path = path + (migration,)
                if migration.target_version == target_version:
                    return next_path
                if migration.target_version not in visited:
                    visited.add(migration.target_version)
                    queue.append((migration.target_version, next_path))
        raise ValueError(f"no migration path from v{source_version} to v{target_version}")


@dataclass(frozen=True)
class MigrationPlan:
    source_version: int
    target_version: int
    source_fingerprint: GraphFingerprint
    migration_ids: tuple[str, ...]
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
            "migration_ids": list(self.migration_ids),
            "output_fingerprint": GraphFingerprint.from_bytes(self.output_bytes).to_dict(),
            "source_fingerprint": self.source_fingerprint.to_dict(),
            "source_version": self.source_version,
            "target_version": self.target_version,
        }


class GraphMigrationService:
    def __init__(self, registry: MigrationRegistry):
        self.registry = registry

    def plan(self, path: str | Path, target_version: int) -> MigrationPlan:
        document = RawGraphDocumentReader().read(path)
        if document.fingerprint is None or not isinstance(document.root, Mapping):
            raise ValueError(f"graph is not migration-ready: {document.status.value}")
        source_version = document.root.get("schema_version", 1)
        if isinstance(source_version, bool) or not isinstance(source_version, int):
            raise ValueError("schema_version must be an integer before migration")
        migrations = self.registry.resolve(source_version, target_version)
        transformed: Mapping[str, Any] = dict(document.root)
        for migration in migrations:
            transformed = dict(migration.transform(transformed))
            if transformed.get("schema_version") != migration.target_version:
                raise ValueError(
                    f"migration {migration.migration_id} did not set schema_version "
                    f"to {migration.target_version}"
                )
        output = json.dumps(
            transformed,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        return MigrationPlan(
            source_version=source_version,
            target_version=target_version,
            source_fingerprint=document.fingerprint,
            migration_ids=tuple(item.migration_id for item in migrations),
            transformed_document=transformed,
            output_bytes=output,
        )

    def execute(
        self,
        plan: MigrationPlan,
        persistence: GraphPersistencePort,
        *,
        confirm_write: bool = False,
        create_backup: bool = False,
    ) -> GraphWriteReceipt:
        if not confirm_write:
            raise ValueError("migration execution requires confirm_write=True")
        return persistence.guarded_write(
            plan.output_bytes,
            expected_fingerprint=plan.source_fingerprint,
            create_backup=create_backup,
        )
