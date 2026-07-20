"""Contracts for deterministic semantic Knowledge Graph consistency rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from services.knowledge_graph.domain import GraphFingerprint, GraphIssue, IssueSeverity
from services.knowledge_graph.domain.issues import json_safe


@dataclass(frozen=True)
class ConsistencyContext:
    nodes: tuple[Mapping[str, Any], ...]
    edges: tuple[Mapping[str, Any], ...]

    @property
    def nodes_by_id(self) -> Mapping[str, Mapping[str, Any]]:
        return MappingProxyType({str(item.get("id")): item for item in self.nodes})


class ConsistencyRule(Protocol):
    rule_id: str
    version: str

    def evaluate(self, context: ConsistencyContext) -> tuple[GraphIssue, ...]: ...


class ConsistencyStatus(str, Enum):
    CONSISTENT = "consistent"
    DEGRADED = "degraded"
    INCONSISTENT = "inconsistent"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class ConsistencyReport:
    status: ConsistencyStatus
    fingerprint: GraphFingerprint | None
    issues: tuple[GraphIssue, ...]
    evaluated_rule_ids: tuple[str, ...]
    can_inform_experience: bool
    can_inform_recommendations: bool
    report_version: str = "1.0.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(sorted(self.issues, key=lambda item: item.sort_key())))
        object.__setattr__(self, "evaluated_rule_ids", tuple(sorted(self.evaluated_rule_ids)))

    @property
    def severity_counts(self) -> Mapping[str, int]:
        counts = Counter(item.severity.value for item in self.issues)
        return MappingProxyType({item.value: counts.get(item.value, 0) for item in IssueSeverity})

    def to_dict(self) -> dict[str, Any]:
        return json_safe({
            "can_inform_experience": self.can_inform_experience,
            "can_inform_recommendations": self.can_inform_recommendations,
            "evaluated_rule_ids": self.evaluated_rule_ids,
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "issues": [item.to_dict() for item in self.issues],
            "report_version": self.report_version,
            "severity_counts": dict(self.severity_counts),
            "status": self.status.value,
        })


@dataclass(frozen=True)
class DomainPackConsistencyRules:
    pack_id: str
    rules: tuple[ConsistencyRule, ...]

    def __post_init__(self) -> None:
        prefix = f"domain_pack.{self.pack_id}."
        if any(not rule.rule_id.startswith(prefix) for rule in self.rules):
            raise ValueError(f"Domain Pack consistency rule ids must start with '{prefix}'")
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("Domain Pack consistency rule ids must be unique")
