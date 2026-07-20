# Knowledge Graph Lifecycle Foundation

## Scope

Milestone 7C introduces explicit lifecycle primitives without registering an
automatic migration or repair. Validation and ordinary consumer reads remain
read-only.

## Migration registry

`MigrationRegistry` stores uniquely identified forward migrations and resolves
a deterministic path between schema versions. Downgrades are rejected. A
`GraphMigrationService.plan()` call:

1. reads the lossless raw document;
2. verifies that its schema version is usable;
3. resolves registered transformations;
4. applies them only in memory;
5. returns a `MigrationPlan` containing migration ids and fingerprints.

Planning never writes. Every transform must explicitly set its declared target
schema version.

## Explicit repairs

No repair rule runs during validation, query, reasoning, or migration.
`GraphRepairService` accepts an explicit ordered tuple of `GraphRepair`
contracts and first returns a dry-run `RepairPlan`. Repair ids are unique and
included in the auditable plan.

## Write safety

Migration and repair execution share `GraphPersistencePort`. The filesystem
adapter requires all of the following:

- `confirm_write=True` at service execution;
- `create_backup=True` at persistence execution;
- an exact match with the raw fingerprint captured by the plan;
- an atomic same-directory file replacement.

The immutable backup name contains the previous fingerprint prefix. A changed
source raises `ConcurrentGraphChange`; an existing backup with different bytes
raises a collision error. The write receipt records previous and resulting
fingerprints together with the backup path.

This foundation does not define a v2 schema, does not auto-discover transforms,
and does not perform writes from existing consumers.
