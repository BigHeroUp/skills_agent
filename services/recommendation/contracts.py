"""Deterministic recommendation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from services.knowledge_graph.domain.issues import freeze_json, json_safe


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_RANK = {risk: index for index, risk in enumerate(ActionRisk)}


@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: str
    action: str
    reason: str
    confidence: float
    evidence_strength: float
    urgency: float = 0.0
    risk: ActionRisk = ActionRisk.LOW
    domain: str = "general"
    contexts: frozenset[str] = field(default_factory=frozenset)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    source: str = "deterministic"

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.action.strip():
            raise ValueError("candidate_id and action must be non-empty")
        for name in ("confidence", "evidence_strength", "urgency"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        object.__setattr__(self, "contexts", frozenset(self.contexts))
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))


@dataclass(frozen=True)
class RecommendationContext:
    domain: str = "general"
    context: str = "analysis"
    maximum_risk: ActionRisk = ActionRisk.MEDIUM
    minimum_confidence: float = 0.35
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        object.__setattr__(self, "metadata", freeze_json(self.metadata))


@dataclass(frozen=True)
class RankedRecommendation:
    rank: int
    candidate_id: str
    action: str
    reason: str
    priority: str
    score: float
    confidence: float
    risk: ActionRisk
    evidence_ids: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, Any]:
        return json_safe({
            "action": self.action,
            "candidate_id": self.candidate_id,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
            "priority": self.priority,
            "rank": self.rank,
            "reason": self.reason,
            "risk": self.risk.value,
            "score": self.score,
            "source": self.source,
        })


@dataclass(frozen=True)
class RecommendationResult:
    status: str
    recommendations: tuple[RankedRecommendation, ...]
    rejected_candidate_ids: tuple[str, ...]
    policy_id: str
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "rejected_candidate_ids": list(self.rejected_candidate_ids),
            "status": self.status,
        }
