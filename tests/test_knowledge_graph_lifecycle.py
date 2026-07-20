import json

import pytest

from services.knowledge_graph.lifecycle import (
    ConcurrentGraphChange,
    FilesystemGraphPersistence,
    GraphMigration,
    GraphMigrationService,
    GraphRepair,
    GraphRepairService,
    MigrationRegistry,
)


def _write(tmp_path, payload):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _migration(identifier, source, target):
    def transform(payload):
        output = dict(payload)
        output["schema_version"] = target
        output.setdefault("migration_history", []).append(identifier)
        return output

    return GraphMigration(identifier, source, target, identifier, transform)


def test_registry_resolves_deterministic_forward_path():
    registry = MigrationRegistry((
        _migration("v1-v2", 1, 2),
        _migration("v2-v3", 2, 3),
        _migration("v1-v3", 1, 3),
    ))

    resolved = registry.resolve(1, 3)

    assert [item.migration_id for item in resolved] == ["v1-v3"]
    assert registry.resolve(2, 2) == ()
    with pytest.raises(ValueError, match="downgrade"):
        registry.resolve(3, 2)


def test_migration_plan_is_dry_run_and_does_not_write(tmp_path):
    path = _write(tmp_path, {"schema_version": 1, "nodes": [], "edges": []})
    before = path.read_bytes()
    service = GraphMigrationService(MigrationRegistry((_migration("v1-v2", 1, 2),)))

    plan = service.plan(path, 2)

    assert plan.to_dict()["dry_run"] is True
    assert plan.migration_ids == ("v1-v2",)
    assert plan.transformed_document["schema_version"] == 2
    assert path.read_bytes() == before


def test_migration_write_requires_confirmation_and_backup(tmp_path):
    path = _write(tmp_path, {"schema_version": 1, "nodes": [], "edges": []})
    service = GraphMigrationService(MigrationRegistry((_migration("v1-v2", 1, 2),)))
    plan = service.plan(path, 2)
    persistence = FilesystemGraphPersistence(path)

    with pytest.raises(ValueError, match="confirm_write"):
        service.execute(plan, persistence)
    with pytest.raises(ValueError, match="create_backup"):
        service.execute(plan, persistence, confirm_write=True)

    receipt = service.execute(
        plan,
        persistence,
        confirm_write=True,
        create_backup=True,
    )

    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2
    assert json.loads(receipt.backup_path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert receipt.previous_fingerprint == plan.source_fingerprint
    assert receipt.current_fingerprint != receipt.previous_fingerprint


def test_guarded_write_rejects_changes_after_plan(tmp_path):
    path = _write(tmp_path, {"schema_version": 1, "nodes": [], "edges": []})
    service = GraphMigrationService(MigrationRegistry((_migration("v1-v2", 1, 2),)))
    plan = service.plan(path, 2)
    path.write_text(
        json.dumps({"schema_version": 1, "nodes": [{"id": "changed"}], "edges": []}),
        encoding="utf-8",
    )

    with pytest.raises(ConcurrentGraphChange):
        service.execute(
            plan,
            FilesystemGraphPersistence(path),
            confirm_write=True,
            create_backup=True,
        )


def test_repairs_are_explicit_dry_run_first_and_auditable(tmp_path):
    path = _write(tmp_path, {"schema_version": 1, "nodes": [], "edges": [], "legacy": True})

    def remove_legacy(payload):
        output = dict(payload)
        output.pop("legacy", None)
        return output

    service = GraphRepairService()
    plan = service.plan(path, (GraphRepair("remove-legacy", "Remove legacy flag", remove_legacy),))

    assert plan.to_dict()["repair_ids"] == ["remove-legacy"]
    assert "legacy" not in plan.transformed_document
    assert json.loads(path.read_text(encoding="utf-8"))["legacy"] is True

    receipt = service.execute(
        plan,
        FilesystemGraphPersistence(path),
        confirm_write=True,
        create_backup=True,
    )
    assert "legacy" not in json.loads(path.read_text(encoding="utf-8"))
    assert receipt.backup_path.exists()
