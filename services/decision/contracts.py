"""Contracts for deterministic analytical decision intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from services.knowledge_graph.domain.issues import json_safe
from services.recommendation import ActionRisk


class EvidenceKind(str, Enum):
    METRIC = "metric"
    ANOMALY = "anomaly"
    ROOT_CAUSE = "root_cause"
    EXPERIENCE = "experience"
    POLICY = "policy"


class DecisionSource(str, Enum):
    STRATEGY = "strategy"
    ANOMALY = "anomaly"
    ROOT_CAUSE = "root_cause"
    RECOMMENDATION = "recommendation"


@dataclass(frozen=True)
class DecisionEvidence:
    evidence_id: str
    kind: EvidenceKind
    strength: float
    reliability: float
    confidence: float
    summary: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        for name in ("strength", "reliability", "confidence"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def score(self) -> float:
        return round(self.strength * self.reliability * self.confidence, 4)


@dataclass(frozen=True)
class DecisionOption:
    option_id: str
    action: str
    source: DecisionSource
    base_confidence: float
    evidence_ids: tuple[str, ...]
    risk: ActionRisk = ActionRisk.LOW

    def __post_init__(self) -> None:
        if not self.option_id.strip() or not self.action.strip():
            raise ValueError("option_id and action must be non-empty")
        if not 0 <= self.base_confidence <= 1:
            raise ValueError("base_confidence must be between 0 and 1")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))


@dataclass(frozen=True)
class RankedDecision:
    rank: int
    option_id: str
    action: str
    source: DecisionSource
    score: float
    evidence_score: float
    evidence_ids: tuple[str, ...]
    missing_evidence_ids: tuple[str, ...]
    risk: ActionRisk

    def to_dict(self) -> dict[str, Any]:
        return json_safe({
            "action": self.action,
            "evidence_ids": self.evidence_ids,
            "evidence_score": self.evidence_score,
            "missing_evidence_ids": self.missing_evidence_ids,
            "option_id": self.option_id,
            "rank": self.rank,
            "risk": self.risk.value,
            "score": self.score,
            "source": self.source.value,
        })


@dataclass(frozen=True)
class DecisionResult:
    status: str
    selected: RankedDecision | None
    ranked_options: tuple[RankedDecision, ...]
    rejected_option_ids: tuple[str, ...]
    policy_id: str
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "ranked_options": [item.to_dict() for item in self.ranked_options],
            "rejected_option_ids": list(self.rejected_option_ids),
            "selected": self.selected.to_dict() if self.selected else None,
            "status": self.status,
        }
