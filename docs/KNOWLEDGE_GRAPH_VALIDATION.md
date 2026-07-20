# Knowledge Graph Lossless Structural Validation

## Scope

Milestone 7A adds a deterministic, offline-first, read-only path for inspecting
the local Knowledge Graph JSON before the legacy store normalizes it.

It does not:

- replace `KnowledgeGraphStore`;
- change the Coordinator or agent order;
- run automatically in query, reasoning, experience, or Kernel paths;
- normalize or create a new graph snapshot;
- calculate a numeric quality score;
- migrate, repair, or rewrite the graph;
- persist raw dataframe rows.

## Flow

```text
path
  -> RawGraphDocumentReader
  -> RawGraphDocument
  -> GovernancePolicy + GraphSchema v1
  -> GraphValidator
  -> GraphValidationResult + GraphQualityReport
```

The raw document retains the exact bytes, the exact decoded text when UTF-8 is
valid, and a SHA-256 fingerprint over the original bytes. Invalid UTF-8 is
classified as corrupt; its original bytes and fingerprint remain available in
memory. The fingerprint does not include an absolute path or runtime timestamp.

## Duplicate JSON keys

The standard JSON decoder is used with `object_pairs_hook`. JSON objects are
first represented as ordered key/value pairs and only then traversed to:

1. build best-effort JSON pointers;
2. record repeated keys;
3. materialize an analyzable mapping.

The original text remains the lossless authority. The analyzable mapping keeps
the last value for a repeated key, but validation reports the duplicate before
any graph normalization. The pointer identifies the repeated key's logical
location; it does not include the byte offset or distinguish each repeated
occurrence with a separate ordinal.

`NaN`, `Infinity`, and `-Infinity` are captured through `parse_constant`,
reported as strict-JSON errors, and never emitted as non-finite floats in the
quality report.

## Validation modes

Both modes emit exactly the same ordered issues.

- `permissive`: individually valid records may be consumed even when other
  records are quarantined. Edges with invalid or missing endpoints are never
  accepted.
- `strict`: `can_consume` is false if any error exists.

`can_write` is a safety signal for future services. It is false whenever an
error or quarantined record exists. Milestone 7A itself never writes.

## Report status precedence

Status precedence is deterministic:

1. `unsupported`: future schema version;
2. `unreadable`: missing, unreadable, empty-file, corrupt, or invalid UTF-8;
3. `invalid`: one or more structural errors;
4. `empty`: valid graph object with no accepted nodes or edges and no errors;
5. `degraded`: warnings or information findings without errors;
6. `valid`: no findings.

An empty JSON file is `unreadable`; a valid object with empty `nodes` and
`edges` arrays is `empty`.

Qualitative dimensions use `pass`, `warn`, `fail`, and `not_evaluated` for:

- document structure;
- identity;
- naming;
- uniqueness;
- referential integrity;
- schema compatibility;
- property completeness;
- graph coverage.

No numeric score is defined in this milestone.

## Schema v1 compatibility

The validator recognizes the node types and relationships currently emitted by
the repository. `USES_DATASET`, `GENERATED_INSIGHT`, and
`PROPOSED_ROOT_CAUSE` remain readable legacy aliases and produce warnings.
The mapper is intentionally unchanged and may continue to emit both canonical
and legacy relationships until a later explicit migration milestone.

An absent `schema_version` may be interpreted as v1 by the v1 governance policy
and always produces a warning. A future schema version is `unsupported`; the
validator does not materialize records or rewrite the source.

## CLI

```bash
python3 scripts/validate_knowledge_graph.py
python3 scripts/validate_knowledge_graph.py --mode strict
python3 scripts/validate_knowledge_graph.py --format json
python3 scripts/validate_knowledge_graph.py --path path/to/knowledge_graph.json
```

Defaults:

- path: `data/knowledge_graph/knowledge_graph.json`;
- mode: `permissive`;
- format: `text`.

Exit codes:

- `0`: valid, degraded, or empty;
- `1`: invalid;
- `2`: unreadable;
- `3`: unsupported.

The JSON output contains privacy-safe structural summaries for accepted and
quarantined records. Arbitrary property values are not repeated in the output.
The raw text remains available only on the in-memory `RawGraphDocument`.

## Governance contracts (Milestone 7B)

Milestone 7B extends the same read-only validation path with explicit lifecycle
metadata. Schema contracts can now declare:

- deprecation metadata (`since`, optional replacement and removal version) for
  node types, node properties and relationships;
- maximum relationship cardinality per source or per target;
- additive Domain Pack schema extensions.

Deprecations produce actionable warnings and never rewrite a document.
Cardinality violations produce deterministic errors; permissive mode can still
expose otherwise accepted records, while strict mode blocks consumption. When a
legacy alias and its canonical relationship connect the same endpoints, they
count as one semantic connection. This preserves compatibility with snapshots
that deliberately emit both forms during staged adoption.

Domain Pack extensions must be passed explicitly in a `GovernancePolicy` and
are composed before document validation. They cannot override core contracts:

- pack ids use `lower_snake_case`;
- node types start with `<pack_id>__`;
- relationships start with `<PACK_ID>__`;
- duplicate pack contributions, name collisions and unknown endpoint types are
  rejected before any graph record is evaluated.

Schema composition creates a new immutable `GraphSchema`; it does not mutate
the core v1 schema, load Domain Packs implicitly, or write graph files.
