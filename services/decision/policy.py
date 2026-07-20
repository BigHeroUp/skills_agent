"""Versioned deterministic decision policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from services.recommendation import ActionRisk

from .contracts import DecisionSource


@dataclass(frozen=True)
class DecisionPolicy:
    policy_id: str = "veraxis.decision.v1"
    version: str = "1.0.0"
    minimum_score: float = 0.4
    base_weight: float = 0.35
    evidence_weight: float = 0.5
    source_weight: float = 0.15
    source_priority: Mapping[DecisionSource, float] = field(default_factory=lambda: {
        DecisionSource.STRATEGY: 0.55,
        DecisionSource.ANOMALY: 0.65,
        DecisionSource.ROOT_CAUSE: 0.85,
        DecisionSource.RECOMMENDATION: 1.0,
    })
    risk_penalty: Mapping[ActionRisk, float] = field(default_factory=lambda: {
        ActionRisk.LOW: 0.0,
        ActionRisk.MEDIUM: 0.08,
        ActionRisk.HIGH: 0.2,
        ActionRisk.CRITICAL: 0.4,
    })

    def __post_init__(self) -> None:
        if round(self.base_weight + self.evidence_weight + self.source_weight, 10) != 1:
            raise ValueError("decision weights must sum to 1")
        if not 0 <= self.minimum_score <= 1:
            raise ValueError("minimum_score must be between 0 and 1")
        object.__setattr__(self, "source_priority", MappingProxyType(dict(self.source_priority)))
        object.__setattr__(self, "risk_penalty", MappingProxyType(dict(self.risk_penalty)))


DEFAULT_DECISION_POLICY = DecisionPolicy()
