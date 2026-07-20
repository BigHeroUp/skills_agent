"""Deterministic structural validator over lossless raw graph documents."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from services.knowledge_graph.domain import (
    GraphIssue,
    IssueSeverity,
    QuarantinedRecord,
    RawGraphDocument,
    RawReadStatus,
)
from services.knowledge_graph.domain.issues import freeze_json, json_safe
from services.knowledge_graph.domain.raw_document import summarize_record
from services.knowledge_graph.governance import GovernancePolicy, ValidationMode

from .report import DimensionStatus, GraphQualityReport, QualityDimension, QualityStatus


LOWER_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
UPPER_SNAKE_CASE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")

DIMENSION_CATEGORIES = {
    "document_structure": {"document_structure"},
    "identity": {"identity"},
    "naming": {"naming"},
    "uniqueness": {"uniqueness"},
    "referential_integrity": {"referential_integrity"},
    "schema_compatibility": {"schema_compatibility"},
    "property_completeness": {"property_completeness"},
    "graph_coverage": {"graph_coverage"},
}


@dataclass(frozen=True)
class GraphValidationResult:
    report: GraphQualityReport
    accepted_nodes: tuple[Any, ...]
    accepted_edges: tuple[Any, ...]
    quarantined_records: tuple[QuarantinedRecord, ...]
    mode: ValidationMode
    is_complete: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "accepted_nodes", tuple(freeze_json(item) for item in self.accepted_nodes))
        object.__setattr__(self, "accepted_edges", tuple(freeze_json(item) for item in self.accepted_edges))
        object.__setattr__(
            self,
            "quarantined_records",
            tuple(sorted(self.quarantined_records, key=lambda item: (item.location, item.kind))),
        )

    @property
    def fingerprint(self):
        return self.report.fingerprint

    @property
    def can_consume(self) -> bool:
        return self.report.can_consume

    @property
    def can_write(self) -> bool:
        return self.report.can_write

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_edges": [summarize_record(item) for item in self.accepted_edges],
            "accepted_nodes": [summarize_record(item) for item in self.accepted_nodes],
            "can_consume": self.can_consume,
            "can_write": self.can_write,
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "is_complete": self.is_complete,
            "mode": self.mode.value,
            "quarantined_records": [item.to_dict() for item in self.quarantined_records],
            "report": self.report.to_dict(),
        }


class GraphValidator:
    RULE_VERSION = "1.0.0"

    def validate(
        self,
        document: RawGraphDocument,
        policy: GovernancePolicy,
        *,
        mode: ValidationMode = ValidationMode.PERMISSIVE,
    ) -> GraphValidationResult:
        issues = list(document.parse_issues)
        accepted_nodes: list[Mapping[str, Any]] = []
        accepted_edges: list[Mapping[str, Any]] = []
        quarantined: list[QuarantinedRecord] = []
        graph_schema_version: int | None = None
        unsupported = False
        fatal_document = document.status in {
            RawReadStatus.MISSING,
            RawReadStatus.UNREADABLE,
            RawReadStatus.EMPTY,
            RawReadStatus.CORRUPT,
        }

        if document.status == RawReadStatus.NON_OBJECT:
            issues.append(self._issue(
                "structure.top_level_not_object",
                IssueSeverity.ERROR,
                "document_structure",
                "/",
                "Il top-level del Knowledge Graph deve essere un oggetto JSON.",
                suggestion="Usare un oggetto con schema_version, nodes ed edges.",
            ))
            fatal_document = True

        for duplicate in document.duplicate_keys:
            issues.append(self._issue(
                "uniqueness.duplicate_json_key",
                IssueSeverity.ERROR,
                "uniqueness",
                duplicate.location,
                f"La chiave JSON '{duplicate.key}' compare più di una volta nello stesso oggetto.",
                evidence={"key": duplicate.key},
                suggestion="Mantenere una sola occorrenza della chiave dopo una revisione esplicita.",
            ))
            if duplicate.location.count("/") <= 1:
                fatal_document = True

        for item in document.non_finite_numbers:
            issues.append(self._issue(
                "structure.non_finite_number",
                IssueSeverity.ERROR,
                "document_structure",
                item.location,
                f"Il valore {item.value} non è valido nel JSON rigoroso.",
                evidence={"value": item.value},
                suggestion="Sostituire il valore con un numero finito o null tramite una modifica esplicita.",
            ))

        root = document.root if isinstance(document.root, Mapping) else None
        if root is not None and not fatal_document:
            graph_schema_version, version_issues, unsupported, version_fatal = self._validate_version(root, policy)
            issues.extend(version_issues)
            fatal_document = fatal_document or version_fatal

            if not unsupported:
                nodes_value = root.get("nodes")
                edges_value = root.get("edges")
                if "nodes" not in root:
                    issues.append(self._required_field_issue("/nodes", "nodes"))
                if "edges" not in root:
                    issues.append(self._required_field_issue("/edges", "edges"))

                if nodes_value is not None and not isinstance(nodes_value, tuple):
                    issues.append(self._issue(
                        "structure.nodes_not_array",
                        IssueSeverity.ERROR,
                        "document_structure",
                        "/nodes",
                        "Il campo nodes deve essere un array JSON.",
                        evidence={"actual_type": type(nodes_value).__name__},
                        suggestion="Convertire nodes in un array senza perdere i record originali.",
                    ))
                    nodes_value = ()
                if edges_value is not None and not isinstance(edges_value, tuple):
                    issues.append(self._issue(
                        "structure.edges_not_array",
                        IssueSeverity.ERROR,
                        "document_structure",
                        "/edges",
                        "Il campo edges deve essere un array JSON.",
                        evidence={"actual_type": type(edges_value).__name__},
                        suggestion="Convertire edges in un array senza perdere i record originali.",
                    ))
                    edges_value = ()

                nodes_value = nodes_value if isinstance(nodes_value, tuple) else ()
                edges_value = edges_value if isinstance(edges_value, tuple) else ()
                accepted_nodes, node_quarantine, node_issues = self._validate_nodes(
                    nodes_value,
                    document,
                    policy,
                )
                issues.extend(node_issues)
                quarantined.extend(node_quarantine)

                accepted_edges, edge_quarantine, edge_issues = self._validate_edges(
                    edges_value,
                    accepted_nodes,
                    document,
                    policy,
                )
                issues.extend(edge_issues)
                quarantined.extend(edge_quarantine)
                issues.extend(self._cardinality_issues(accepted_edges, policy))
                issues.extend(self._orphan_issues(accepted_nodes, accepted_edges, policy))

        unsupported = unsupported or any(issue.code == "schema.future_version" for issue in issues)
        ordered_issues = tuple(sorted(issues, key=lambda item: item.sort_key()))
        error_count = sum(issue.severity == IssueSeverity.ERROR for issue in ordered_issues)
        unreadable = document.status in {
            RawReadStatus.MISSING,
            RawReadStatus.UNREADABLE,
            RawReadStatus.EMPTY,
            RawReadStatus.CORRUPT,
        }
        graph_is_empty = bool(root is not None and not accepted_nodes and not accepted_edges and not error_count)

        if unsupported:
            status = QualityStatus.UNSUPPORTED
        elif unreadable:
            status = QualityStatus.UNREADABLE
        elif error_count:
            status = QualityStatus.INVALID
        elif graph_is_empty:
            status = QualityStatus.EMPTY
        elif any(issue.severity in {IssueSeverity.WARNING, IssueSeverity.INFO} for issue in ordered_issues):
            status = QualityStatus.DEGRADED
        else:
            status = QualityStatus.VALID

        has_accepted_content = bool(accepted_nodes or accepted_edges)
        valid_empty_graph = bool(root is not None and not accepted_nodes and not accepted_edges and not error_count)
        permissive_consumable = not fatal_document and not unsupported and (has_accepted_content or valid_empty_graph)
        can_consume = permissive_consumable and (
            mode == ValidationMode.PERMISSIVE or error_count == 0
        )
        can_write = not fatal_document and not unsupported and error_count == 0 and not quarantined
        coverage = self._coverage(root, accepted_nodes, accepted_edges, quarantined)
        dimensions = self._dimensions(ordered_issues, not_evaluated=fatal_document or unsupported)
        report = GraphQualityReport(
            status=status,
            graph_schema_version=graph_schema_version,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            fingerprint=document.fingerprint,
            issues=ordered_issues,
            dimensions=dimensions,
            coverage=coverage,
            can_consume=can_consume,
            can_write=can_write,
            accepted_node_count=len(accepted_nodes),
            accepted_edge_count=len(accepted_edges),
            quarantined_record_count=len(quarantined),
        )
        return GraphValidationResult(
            report=report,
            accepted_nodes=tuple(accepted_nodes),
            accepted_edges=tuple(accepted_edges),
            quarantined_records=tuple(quarantined),
            mode=mode,
            is_complete=not quarantined and error_count == 0,
        )

    def _validate_version(
        self,
        root: Mapping[str, Any],
        policy: GovernancePolicy,
    ) -> tuple[int | None, list[GraphIssue], bool, bool]:
        issues: list[GraphIssue] = []
        if "schema_version" not in root:
            if policy.allow_missing_schema_version_as_v1:
                issues.append(self._issue(
                    "schema.version_missing_assumed_v1",
                    IssueSeverity.WARNING,
                    "schema_compatibility",
                    "/schema_version",
                    "schema_version è assente; la policy legacy interpreta il documento come v1.",
                    suggestion="Aggiungere schema_version=1 con una modifica esplicita.",
                ))
                return 1, issues, False, False
            issues.append(self._issue(
                "schema.version_missing",
                IssueSeverity.ERROR,
                "schema_compatibility",
                "/schema_version",
                "schema_version è obbligatorio.",
                suggestion="Specificare una versione supportata.",
            ))
            return None, issues, False, True

        value = root.get("schema_version")
        if isinstance(value, bool) or not isinstance(value, int):
            issues.append(self._issue(
                "schema.version_not_integer",
                IssueSeverity.ERROR,
                "schema_compatibility",
                "/schema_version",
                "schema_version deve essere un intero.",
                evidence={"actual_type": type(value).__name__},
                suggestion="Usare un intero senza riscrittura automatica.",
            ))
            return None, issues, False, True
        if value > policy.schema.version:
            issues.append(self._issue(
                "schema.future_version",
                IssueSeverity.ERROR,
                "schema_compatibility",
                "/schema_version",
                "La versione del documento è più recente di quella supportata.",
                evidence={"supported": policy.schema.version, "actual": value},
                suggestion="Usare un runtime compatibile; non risalvare il documento con questa versione.",
            ))
            return value, issues, True, True
        if value < 1:
            issues.append(self._issue(
                "schema.version_invalid",
                IssueSeverity.ERROR,
                "schema_compatibility",
                "/schema_version",
                "schema_version deve essere maggiore o uguale a 1.",
                evidence={"actual": value},
                suggestion="Correggere la versione tramite una migrazione esplicita.",
            ))
            return value, issues, False, True
        return value, issues, False, False

    def _validate_nodes(
        self,
        records: tuple[Any, ...],
        document: RawGraphDocument,
        policy: GovernancePolicy,
    ) -> tuple[list[Mapping[str, Any]], list[QuarantinedRecord], list[GraphIssue]]:
        accepted: list[Mapping[str, Any]] = []
        quarantined: list[QuarantinedRecord] = []
        issues: list[GraphIssue] = []
        id_counts = Counter(
            record.get("id")
            for record in records
            if isinstance(record, Mapping)
            and isinstance(record.get("id"), str)
            and record.get("id").strip()
        )
        non_finite_locations = {item.location for item in document.non_finite_numbers}
        duplicate_locations = {item.location for item in document.duplicate_keys}

        for index, record in enumerate(records):
            location = f"/nodes/{index}"
            reason_codes: list[str] = []
            if not isinstance(record, Mapping):
                issue = self._issue(
                    "structure.node_not_object",
                    IssueSeverity.ERROR,
                    "document_structure",
                    location,
                    "Ogni record nodo deve essere un oggetto JSON.",
                    evidence={"actual_type": type(record).__name__},
                    suggestion="Sostituire il record solo dopo revisione esplicita.",
                )
                issues.append(issue)
                quarantined.append(QuarantinedRecord("node", location, record, (issue.code,)))
                continue

            node_id = record.get("id")
            node_type = record.get("type")
            if "id" not in record or not isinstance(node_id, str) or not node_id.strip():
                issues.append(self._issue(
                    "identity.node_id_missing_or_empty",
                    IssueSeverity.ERROR,
                    "identity",
                    f"{location}/id",
                    "Il nodo deve avere un ID stringa non vuoto.",
                    suggestion="Assegnare un ID stabile e namespaced.",
                ))
                reason_codes.append("identity.node_id_missing_or_empty")
            elif id_counts[node_id] > 1:
                issues.append(self._issue(
                    "uniqueness.duplicate_node_id",
                    IssueSeverity.ERROR,
                    "uniqueness",
                    f"{location}/id",
                    f"L'ID nodo '{node_id}' compare {id_counts[node_id]} volte nel payload raw.",
                    evidence={"id": node_id, "occurrence_count": id_counts[node_id]},
                    suggestion="Risolvere esplicitamente tutte le occorrenze prima del consumo.",
                ))
                reason_codes.append("uniqueness.duplicate_node_id")

            if "type" not in record or not isinstance(node_type, str) or not node_type.strip():
                issues.append(self._issue(
                    "structure.node_type_missing",
                    IssueSeverity.ERROR,
                    "document_structure",
                    f"{location}/type",
                    "Il nodo deve avere un type stringa non vuoto.",
                    suggestion="Assegnare un node type definito dallo schema.",
                ))
                reason_codes.append("structure.node_type_missing")
            elif not LOWER_SNAKE_CASE.fullmatch(node_type):
                issues.append(self._issue(
                    "naming.node_type_not_lower_snake_case",
                    IssueSeverity.WARNING,
                    "naming",
                    f"{location}/type",
                    "Il node type non segue lower_snake_case.",
                    evidence={"type": node_type},
                    suggestion="Usare lower_snake_case in una futura migrazione esplicita.",
                ))

            node_spec = policy.schema.node_spec(str(node_type or ""))
            if node_type and node_spec is None:
                issues.append(self._issue(
                    "schema.unknown_node_type",
                    policy.unknown_node_type_severity,
                    "schema_compatibility",
                    f"{location}/type",
                    f"Il node type '{node_type}' non è definito nello schema v1.",
                    evidence={"type": node_type},
                    suggestion="Registrare il tipo in una policy futura o verificare il payload.",
                ))
            elif node_spec and node_spec.deprecation:
                issues.append(self._deprecation_issue(
                    "schema.deprecated_node_type",
                    f"{location}/type",
                    str(node_type),
                    node_spec.deprecation,
                ))

            label = record.get("label")
            if "label" not in record or not isinstance(label, str) or not label.strip():
                issues.append(self._issue(
                    "property.node_label_missing_or_empty",
                    policy.missing_label_severity,
                    "property_completeness",
                    f"{location}/label",
                    "Il nodo non ha una label stringa non vuota.",
                    suggestion="Aggiungere una label descrittiva senza cambiare l'identità del nodo.",
                ))

            properties = record.get("properties")
            if "properties" not in record:
                issues.append(self._issue(
                    "property.node_properties_missing",
                    policy.missing_properties_severity,
                    "property_completeness",
                    f"{location}/properties",
                    "Il campo properties è assente.",
                    suggestion="Aggiungere un oggetto properties, anche vuoto.",
                ))
                properties = {}
            elif not isinstance(properties, Mapping):
                issues.append(self._issue(
                    "structure.node_properties_not_object",
                    IssueSeverity.ERROR,
                    "document_structure",
                    f"{location}/properties",
                    "Il campo properties del nodo deve essere un oggetto JSON.",
                    evidence={"actual_type": type(properties).__name__},
                    suggestion="Convertire properties solo tramite modifica esplicita.",
                ))
                reason_codes.append("structure.node_properties_not_object")
                properties = {}

            issues.extend(self._property_issues(properties, f"{location}/properties"))
            if node_spec:
                for property_spec in node_spec.properties:
                    name = property_spec.name
                    if name not in properties:
                        if not property_spec.required:
                            continue
                        issues.append(self._issue(
                            "property.required_node_property_missing",
                            IssueSeverity.ERROR,
                            "property_completeness",
                            f"{location}/properties/{name}",
                            f"La proprietà obbligatoria '{name}' è assente per {node_type}.",
                            evidence={"node_type": node_type, "property": name},
                            suggestion="Aggiungere la proprietà da una fonte verificabile.",
                        ))
                        reason_codes.append("property.required_node_property_missing")
                    elif property_spec.deprecation:
                        issues.append(self._deprecation_issue(
                            "schema.deprecated_node_property",
                            f"{location}/properties/{name}",
                            f"{node_type}.{name}",
                            property_spec.deprecation,
                        ))
                for name in node_spec.recommended_properties:
                    if name not in properties:
                        issues.append(self._issue(
                            "property.recommended_node_property_missing",
                            IssueSeverity.WARNING,
                            "property_completeness",
                            f"{location}/properties/{name}",
                            f"La proprietà raccomandata '{name}' è assente per {node_type}.",
                            evidence={"node_type": node_type, "property": name},
                            suggestion="Valutare l'aggiunta della proprietà in un aggiornamento esplicito.",
                        ))

            if any(path == location or path.startswith(f"{location}/") for path in non_finite_locations):
                reason_codes.append("structure.non_finite_number")
            if any(path == location or path.startswith(f"{location}/") for path in duplicate_locations):
                reason_codes.append("uniqueness.duplicate_json_key")

            if reason_codes:
                quarantined.append(QuarantinedRecord("node", location, record, tuple(reason_codes)))
            else:
                accepted.append(record)
        return accepted, quarantined, issues

    def _validate_edges(
        self,
        records: tuple[Any, ...],
        accepted_nodes: list[Mapping[str, Any]],
        document: RawGraphDocument,
        policy: GovernancePolicy,
    ) -> tuple[list[Mapping[str, Any]], list[QuarantinedRecord], list[GraphIssue]]:
        accepted: list[Mapping[str, Any]] = []
        quarantined: list[QuarantinedRecord] = []
        issues: list[GraphIssue] = []
        nodes_by_id = {str(node.get("id")): node for node in accepted_nodes}
        edge_counts = Counter(
            (
                record.get("source"),
                record.get("target"),
                record.get("relationship"),
            )
            for record in records
            if isinstance(record, Mapping)
            and all(
                isinstance(record.get(field_name), str) and record.get(field_name).strip()
                for field_name in ("source", "target", "relationship")
            )
        )
        non_finite_locations = {item.location for item in document.non_finite_numbers}
        duplicate_locations = {item.location for item in document.duplicate_keys}

        for index, record in enumerate(records):
            location = f"/edges/{index}"
            reason_codes: list[str] = []
            if not isinstance(record, Mapping):
                issue = self._issue(
                    "structure.edge_not_object",
                    IssueSeverity.ERROR,
                    "document_structure",
                    location,
                    "Ogni record arco deve essere un oggetto JSON.",
                    evidence={"actual_type": type(record).__name__},
                    suggestion="Sostituire il record solo dopo revisione esplicita.",
                )
                issues.append(issue)
                quarantined.append(QuarantinedRecord("edge", location, record, (issue.code,)))
                continue

            values: dict[str, str] = {}
            for field_name in ("source", "target", "relationship"):
                value = record.get(field_name)
                if field_name not in record or not isinstance(value, str) or not value.strip():
                    code = f"structure.edge_{field_name}_missing_or_empty"
                    issues.append(self._issue(
                        code,
                        IssueSeverity.ERROR,
                        "document_structure",
                        f"{location}/{field_name}",
                        f"L'arco deve avere {field_name} come stringa non vuota.",
                        suggestion=f"Specificare {field_name} usando un valore verificabile.",
                    ))
                    reason_codes.append(code)
                    values[field_name] = ""
                else:
                    values[field_name] = value

            source = values.get("source", "")
            target = values.get("target", "")
            relationship = values.get("relationship", "")
            triple = (source, target, relationship)
            if all(triple) and edge_counts[triple] > 1:
                issues.append(self._issue(
                    "uniqueness.duplicate_edge",
                    IssueSeverity.ERROR,
                    "uniqueness",
                    location,
                    "La tripla source, target e relationship compare più volte nel payload raw.",
                    evidence={
                        "occurrence_count": edge_counts[triple],
                        "relationship": relationship,
                        "source": source,
                        "target": target,
                    },
                    suggestion="Risolvere esplicitamente tutte le occorrenze prima del consumo.",
                ))
                reason_codes.append("uniqueness.duplicate_edge")

            if relationship and not UPPER_SNAKE_CASE.fullmatch(relationship):
                issues.append(self._issue(
                    "naming.relationship_not_upper_snake_case",
                    IssueSeverity.WARNING,
                    "naming",
                    f"{location}/relationship",
                    "La relationship non segue UPPER_SNAKE_CASE.",
                    evidence={"relationship": relationship},
                    suggestion="Usare UPPER_SNAKE_CASE in una futura migrazione esplicita.",
                ))

            relationship_spec = policy.schema.relationship_spec(relationship)
            if relationship and relationship_spec is None:
                issues.append(self._issue(
                    "schema.unknown_relationship",
                    policy.unknown_relationship_severity,
                    "schema_compatibility",
                    f"{location}/relationship",
                    f"La relationship '{relationship}' non è definita nello schema v1.",
                    evidence={"relationship": relationship},
                    suggestion="Registrare la relazione in una policy futura o verificare il payload.",
                ))
            elif relationship_spec and relationship_spec.is_legacy_alias:
                issues.append(self._issue(
                    "schema.legacy_relationship_alias",
                    IssueSeverity.WARNING,
                    "schema_compatibility",
                    f"{location}/relationship",
                    f"La relationship '{relationship}' è un alias legacy.",
                    evidence={
                        "alias": relationship,
                        "canonical": relationship_spec.canonical_name,
                    },
                    suggestion="Continuare a leggerla; convertirla solo tramite migration esplicita.",
                ))
            elif relationship_spec and relationship_spec.deprecation:
                issues.append(self._deprecation_issue(
                    "schema.deprecated_relationship",
                    f"{location}/relationship",
                    relationship,
                    relationship_spec.deprecation,
                ))

            if source and source not in nodes_by_id:
                issues.append(self._issue(
                    "referential.dangling_source",
                    IssueSeverity.ERROR,
                    "referential_integrity",
                    f"{location}/source",
                    f"Il source '{source}' non identifica un nodo accettato.",
                    evidence={"source": source},
                    suggestion="Ripristinare il nodo o rimuovere l'arco tramite repair esplicita futura.",
                ))
                reason_codes.append("referential.dangling_source")
            if target and target not in nodes_by_id:
                issues.append(self._issue(
                    "referential.dangling_target",
                    IssueSeverity.ERROR,
                    "referential_integrity",
                    f"{location}/target",
                    f"Il target '{target}' non identifica un nodo accettato.",
                    evidence={"target": target},
                    suggestion="Ripristinare il nodo o rimuovere l'arco tramite repair esplicita futura.",
                ))
                reason_codes.append("referential.dangling_target")

            if source and target and source == target and (
                relationship_spec is None or not relationship_spec.allows_self_loop
            ):
                issues.append(self._issue(
                    "referential.self_loop_not_allowed",
                    IssueSeverity.ERROR,
                    "referential_integrity",
                    location,
                    "La policy v1 non consente questo self-loop.",
                    evidence={"node_id": source, "relationship": relationship},
                    suggestion="Rimuovere il self-loop solo dopo verifica esplicita.",
                ))
                reason_codes.append("referential.self_loop_not_allowed")

            if relationship_spec and source in nodes_by_id and target in nodes_by_id:
                source_type = str(nodes_by_id[source].get("type") or "")
                target_type = str(nodes_by_id[target].get("type") or "")
                if (
                    source_type not in relationship_spec.source_types
                    or target_type not in relationship_spec.target_types
                ):
                    issues.append(self._issue(
                        "referential.endpoint_type_mismatch",
                        IssueSeverity.ERROR,
                        "referential_integrity",
                        location,
                        "I tipi degli endpoint non sono compatibili con la relationship.",
                        evidence={
                            "relationship": relationship,
                            "source_type": source_type,
                            "target_type": target_type,
                        },
                        suggestion="Correggere endpoint o relationship tramite modifica esplicita.",
                    ))
                    reason_codes.append("referential.endpoint_type_mismatch")

            properties = record.get("properties")
            if "properties" not in record:
                issues.append(self._issue(
                    "property.edge_properties_missing",
                    policy.missing_properties_severity,
                    "property_completeness",
                    f"{location}/properties",
                    "Il campo properties dell'arco è assente.",
                    suggestion="Aggiungere un oggetto properties, anche vuoto.",
                ))
                properties = {}
            elif not isinstance(properties, Mapping):
                issues.append(self._issue(
                    "structure.edge_properties_not_object",
                    IssueSeverity.ERROR,
                    "document_structure",
                    f"{location}/properties",
                    "Il campo properties dell'arco deve essere un oggetto JSON.",
                    evidence={"actual_type": type(properties).__name__},
                    suggestion="Convertire properties solo tramite modifica esplicita.",
                ))
                reason_codes.append("structure.edge_properties_not_object")
                properties = {}
            issues.extend(self._property_issues(properties, f"{location}/properties"))

            if any(path == location or path.startswith(f"{location}/") for path in non_finite_locations):
                reason_codes.append("structure.non_finite_number")
            if any(path == location or path.startswith(f"{location}/") for path in duplicate_locations):
                reason_codes.append("uniqueness.duplicate_json_key")

            if reason_codes:
                quarantined.append(QuarantinedRecord("edge", location, record, tuple(reason_codes)))
            else:
                accepted.append(record)
        return accepted, quarantined, issues

    def _cardinality_issues(
        self,
        edges: list[Mapping[str, Any]],
        policy: GovernancePolicy,
    ) -> list[GraphIssue]:
        by_source: dict[tuple[str, str], set[str]] = defaultdict(set)
        by_target: dict[tuple[str, str], set[str]] = defaultdict(set)
        specs = {}
        for edge in edges:
            relationship = str(edge.get("relationship") or "")
            spec = policy.schema.relationship_spec(relationship)
            if not spec:
                continue
            canonical = spec.canonical_name or relationship
            specs[canonical] = spec
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            by_source[(canonical, source)].add(target)
            by_target[(canonical, target)].add(source)

        issues: list[GraphIssue] = []
        for (relationship, source), targets in sorted(by_source.items()):
            count = len(targets)
            maximum = specs[relationship].cardinality.max_per_source
            if maximum is not None and count > maximum:
                issues.append(self._issue(
                    "cardinality.max_per_source_exceeded",
                    IssueSeverity.ERROR,
                    "referential_integrity",
                    f"/nodes[id={source}]",
                    "Il numero di archi in uscita supera la cardinalità consentita.",
                    evidence={
                        "actual": count,
                        "maximum": maximum,
                        "relationship": relationship,
                        "source": source,
                    },
                    suggestion="Risolvere l'ambiguità tramite una modifica esplicita e auditabile.",
                ))
        for (relationship, target), sources in sorted(by_target.items()):
            count = len(sources)
            maximum = specs[relationship].cardinality.max_per_target
            if maximum is not None and count > maximum:
                issues.append(self._issue(
                    "cardinality.max_per_target_exceeded",
                    IssueSeverity.ERROR,
                    "referential_integrity",
                    f"/nodes[id={target}]",
                    "Il numero di archi in ingresso supera la cardinalità consentita.",
                    evidence={
                        "actual": count,
                        "maximum": maximum,
                        "relationship": relationship,
                        "target": target,
                    },
                    suggestion="Risolvere l'ambiguità tramite una modifica esplicita e auditabile.",
                ))
        return issues

    def _deprecation_issue(self, code, location, name, deprecation) -> GraphIssue:
        evidence = {"name": name, "since": deprecation.since}
        if deprecation.replacement:
            evidence["replacement"] = deprecation.replacement
        if deprecation.removal_version is not None:
            evidence["removal_version"] = deprecation.removal_version
        return self._issue(
            code,
            IssueSeverity.WARNING,
            "schema_compatibility",
            location,
            f"'{name}' è deprecato dalla versione {deprecation.since}.",
            evidence=evidence,
            suggestion=(
                f"Preferire '{deprecation.replacement}' nei nuovi documenti; "
                "migrare i documenti esistenti solo esplicitamente."
                if deprecation.replacement
                else "Non usarlo nei nuovi documenti; migrare quelli esistenti solo esplicitamente."
            ),
        )

    def _property_issues(self, properties: Mapping[str, Any], location: str) -> list[GraphIssue]:
        issues = []
        for key in sorted(properties, key=str):
            clean_key = str(key)
            if not LOWER_SNAKE_CASE.fullmatch(clean_key):
                issues.append(self._issue(
                    "naming.property_key_not_lower_snake_case",
                    IssueSeverity.WARNING,
                    "naming",
                    f"{location}/{clean_key}",
                    "La property key non segue lower_snake_case.",
                    evidence={"property": clean_key},
                    suggestion="Rinominare la proprietà soltanto tramite migration esplicita.",
                ))
        return issues

    def _orphan_issues(
        self,
        nodes: list[Mapping[str, Any]],
        edges: list[Mapping[str, Any]],
        policy: GovernancePolicy,
    ) -> list[GraphIssue]:
        degree = Counter()
        for edge in edges:
            degree.update([str(edge.get("source") or ""), str(edge.get("target") or "")])
        issues = []
        for node in sorted(nodes, key=lambda item: str(item.get("id") or "")):
            node_id = str(node.get("id") or "")
            if not node_id or degree[node_id] > 0:
                continue
            node_type = str(node.get("type") or "")
            spec = policy.schema.node_spec(node_type)
            severity_name = spec.isolated_severity if spec else "warning"
            severity = IssueSeverity(severity_name)
            issues.append(self._issue(
                "coverage.isolated_node",
                severity,
                "graph_coverage",
                f"/nodes[id={node_id}]",
                f"Il nodo '{node_id}' non è collegato da alcun arco accettato.",
                evidence={"id": node_id, "type": node_type},
                suggestion="Verificare se il nodo isolato è legittimo; non rimuoverlo automaticamente.",
            ))
        return issues

    def _coverage(
        self,
        root: Mapping[str, Any] | None,
        nodes: list[Mapping[str, Any]],
        edges: list[Mapping[str, Any]],
        quarantined: list[QuarantinedRecord],
    ) -> dict[str, Any]:
        raw_nodes = root.get("nodes", ()) if root else ()
        raw_edges = root.get("edges", ()) if root else ()
        node_total = len(raw_nodes) if isinstance(raw_nodes, tuple) else 0
        edge_total = len(raw_edges) if isinstance(raw_edges, tuple) else 0
        node_quarantined = sum(item.kind == "node" for item in quarantined)
        edge_quarantined = sum(item.kind == "edge" for item in quarantined)
        return {
            "accepted_edges": len(edges),
            "accepted_nodes": len(nodes),
            "edge_acceptance_ratio": round(len(edges) / edge_total, 6) if edge_total else None,
            "edge_records_total": edge_total,
            "node_acceptance_ratio": round(len(nodes) / node_total, 6) if node_total else None,
            "node_records_total": node_total,
            "quarantined_edges": edge_quarantined,
            "quarantined_nodes": node_quarantined,
        }

    def _dimensions(
        self,
        issues: tuple[GraphIssue, ...],
        *,
        not_evaluated: bool,
    ) -> tuple[QualityDimension, ...]:
        dimensions = []
        for name, categories in DIMENSION_CATEGORIES.items():
            relevant = [issue for issue in issues if issue.category in categories]
            errors = sum(issue.severity == IssueSeverity.ERROR for issue in relevant)
            warnings = sum(issue.severity == IssueSeverity.WARNING for issue in relevant)
            infos = sum(issue.severity == IssueSeverity.INFO for issue in relevant)
            if not_evaluated and name not in {"document_structure", "schema_compatibility"}:
                status = DimensionStatus.NOT_EVALUATED
            elif errors:
                status = DimensionStatus.FAIL
            elif warnings or infos:
                status = DimensionStatus.WARN
            else:
                status = DimensionStatus.PASS
            dimensions.append(QualityDimension(name, status, errors, warnings, infos))
        return tuple(dimensions)

    def _required_field_issue(self, location: str, field_name: str) -> GraphIssue:
        return self._issue(
            "structure.required_top_level_field_missing",
            IssueSeverity.ERROR,
            "document_structure",
            location,
            f"Il campo top-level '{field_name}' è obbligatorio.",
            evidence={"field": field_name},
            suggestion=f"Aggiungere il campo {field_name} senza riscrittura automatica.",
        )

    def _issue(
        self,
        code: str,
        severity: IssueSeverity,
        category: str,
        location: str,
        message: str,
        *,
        evidence: dict[str, Any] | None = None,
        suggestion: str,
    ) -> GraphIssue:
        return GraphIssue(
            code=code,
            severity=severity,
            category=category,
            location=location,
            message=message,
            evidence=evidence or {},
            suggestion=suggestion,
            rule_id=f"core.structural.{code}",
            rule_version=self.RULE_VERSION,
        )
