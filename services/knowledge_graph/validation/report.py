"""Immutable qualitative report for structural graph validation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from services.knowledge_graph.domain import GraphFingerprint, GraphIssue, IssueSeverity
from services.knowledge_graph.domain.issues import freeze_json, json_safe


class QualityStatus(str, Enum):
    VALID = "valid"
    DEGRADED = "degraded"
    INVALID = "invalid"
    EMPTY = "empty"
    UNREADABLE = "unreadable"
    UNSUPPORTED = "unsupported"


class DimensionStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class QualityDimension:
    name: str
    status: DimensionStatus
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_count": self.error_count,
            "info_count": self.info_count,
            "name": self.name,
            "status": self.status.value,
            "warning_count": self.warning_count,
        }


@dataclass(frozen=True)
class GraphQualityReport:
    """Strict-JSON-safe report with no clock-derived fields or numeric score."""

    status: QualityStatus
    graph_schema_version: int | None
    policy_id: str
    policy_version: str
    fingerprint: GraphFingerprint | None
    issues: tuple[GraphIssue, ...]
    dimensions: tuple[QualityDimension, ...]
    coverage: Mapping[str, Any]
    can_consume: bool
    can_write: bool
    accepted_node_count: int
    accepted_edge_count: int
    quarantined_record_count: int
    report_version: str = "1.0.0"
    severity_counts: Mapping[str, int] = field(init=False)
    category_counts: Mapping[str, int] = field(init=False)

    def __post_init__(self) -> None:
        ordered_issues = tuple(sorted(self.issues, key=lambda item: item.sort_key()))
        object.__setattr__(self, "issues", ordered_issues)
        severity_counts = Counter(issue.severity.value for issue in ordered_issues)
        category_counts = Counter(issue.category for issue in ordered_issues)
        object.__setattr__(
            self,
            "severity_counts",
            MappingProxyType({
                severity.value: severity_counts.get(severity.value, 0)
                for severity in IssueSeverity
            }),
        )
        object.__setattr__(
            self,
            "category_counts",
            MappingProxyType(dict(sorted(category_counts.items()))),
        )
        object.__setattr__(self, "coverage", freeze_json(self.coverage))
        object.__setattr__(self, "dimensions", tuple(sorted(self.dimensions, key=lambda item: item.name)))

    @property
    def has_errors(self) -> bool:
        return self.severity_counts.get(IssueSeverity.ERROR.value, 0) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_edge_count": self.accepted_edge_count,
            "accepted_node_count": self.accepted_node_count,
            "can_consume": self.can_consume,
            "can_write": self.can_write,
            "category_counts": dict(self.category_counts),
            "coverage": json_safe(self.coverage),
            "dimensions": [item.to_dict() for item in self.dimensions],
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "graph_schema_version": self.graph_schema_version,
            "issues": [issue.to_dict() for issue in self.issues],
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "quarantined_record_count": self.quarantined_record_count,
            "report_version": self.report_version,
            "severity_counts": dict(self.severity_counts),
            "status": self.status.value,
        }
