"""Schema description matching Knowledge Graph snapshots currently emitted by the repository."""

from __future__ import annotations

from .contracts import (
    CardinalitySpec,
    DeprecationSpec,
    GraphSchema,
    NodeTypeSpec,
    PropertySpec,
    RelationshipSpec,
)


def _properties(*, required: tuple[str, ...] = (), recommended: tuple[str, ...] = ()) -> tuple[PropertySpec, ...]:
    return tuple(
        [PropertySpec(name=name, required=True) for name in required]
        + [PropertySpec(name=name, recommended=True) for name in recommended]
    )


NODE_TYPES = {
    "python_file": NodeTypeSpec(
        "python_file",
        _properties(required=("path",)),
        isolated_severity="info",
    ),
    "python_class": NodeTypeSpec(
        "python_class",
        _properties(required=("file", "qualname", "line")),
    ),
    "python_function": NodeTypeSpec(
        "python_function",
        _properties(required=("file", "qualname", "line"), recommended=("async",)),
    ),
    "python_import": NodeTypeSpec(
        "python_import",
        _properties(required=("module", "imported_name")),
    ),
    "analysis_run": NodeTypeSpec(
        "analysis_run",
        _properties(recommended=("created_at", "source_type", "row_count", "column_count")),
        isolated_severity="warning",
    ),
    "dataset": NodeTypeSpec(
        "dataset",
        _properties(recommended=("source_type", "row_count", "column_count")),
    ),
    "dataframe_column": NodeTypeSpec(
        "dataframe_column",
        _properties(recommended=("name", "dtype")),
    ),
    "insight": NodeTypeSpec("insight", _properties(recommended=("summary",))),
    "anomaly": NodeTypeSpec(
        "anomaly",
        _properties(recommended=("severity", "affected_column")),
    ),
    "root_cause": NodeTypeSpec(
        "root_cause",
        _properties(recommended=("affected_metrics",)),
    ),
    "report": NodeTypeSpec("report", _properties(recommended=("length_chars",))),
    "domain_pack": NodeTypeSpec("domain_pack", _properties(recommended=("pack_id",))),
}


def _relationship(
    name: str,
    sources: tuple[str, ...],
    targets: tuple[str, ...],
    *,
    canonical_name: str | None = None,
    max_per_source: int | None = None,
) -> RelationshipSpec:
    return RelationshipSpec(
        name=name,
        source_types=frozenset(sources),
        target_types=frozenset(targets),
        canonical_name=canonical_name,
        cardinality=CardinalitySpec(max_per_source=max_per_source),
        deprecation=(
            DeprecationSpec(since="1.0.0", replacement=canonical_name)
            if canonical_name
            else None
        ),
    )


RELATIONSHIPS = {
    "CONTAINS": _relationship(
        "CONTAINS",
        ("python_file", "python_class", "python_function"),
        ("python_class", "python_function"),
    ),
    "IMPORTS": _relationship("IMPORTS", ("python_file",), ("python_import",)),
    "ANALYZED_DATASET": _relationship(
        "ANALYZED_DATASET", ("analysis_run",), ("dataset",), max_per_source=1
    ),
    "USES_DATASET": _relationship(
        "USES_DATASET",
        ("analysis_run",),
        ("dataset",),
        canonical_name="ANALYZED_DATASET",
        max_per_source=1,
    ),
    "PRODUCED_INSIGHT": _relationship("PRODUCED_INSIGHT", ("analysis_run",), ("insight",)),
    "GENERATED_INSIGHT": _relationship(
        "GENERATED_INSIGHT",
        ("analysis_run",),
        ("insight",),
        canonical_name="PRODUCED_INSIGHT",
    ),
    "IDENTIFIED_ROOT_CAUSE": _relationship(
        "IDENTIFIED_ROOT_CAUSE",
        ("analysis_run",),
        ("root_cause",),
    ),
    "PROPOSED_ROOT_CAUSE": _relationship(
        "PROPOSED_ROOT_CAUSE",
        ("analysis_run",),
        ("root_cause",),
        canonical_name="IDENTIFIED_ROOT_CAUSE",
    ),
    "HAS_COLUMN": _relationship(
        "HAS_COLUMN",
        ("analysis_run", "dataset"),
        ("dataframe_column",),
    ),
    "DETECTED_ANOMALY": _relationship("DETECTED_ANOMALY", ("analysis_run",), ("anomaly",)),
    "OBSERVED_IN_DATASET": _relationship("OBSERVED_IN_DATASET", ("anomaly",), ("dataset",)),
    "EXPLAINS_ANOMALY": _relationship("EXPLAINS_ANOMALY", ("root_cause",), ("anomaly",)),
    "GENERATED_REPORT": _relationship(
        "GENERATED_REPORT", ("analysis_run",), ("report",), max_per_source=1
    ),
    "USED_DOMAIN_PACK": _relationship(
        "USED_DOMAIN_PACK", ("analysis_run",), ("domain_pack",), max_per_source=1
    ),
}


GRAPH_SCHEMA_V1 = GraphSchema(
    schema_id="veraxis.knowledge_graph",
    version=1,
    node_types=NODE_TYPES,
    relationships=RELATIONSHIPS,
)
