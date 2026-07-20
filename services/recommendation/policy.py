"""Policy for context, domain, evidence, and risk-aware recommendation ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .contracts import ActionRisk


@dataclass(frozen=True)
class RecommendationPolicy:
    policy_id: str = "veraxis.recommendation.v1"
    version: str = "1.0.0"
    confidence_weight: float = 0.5
    evidence_weight: float = 0.3
    urgency_weight: float = 0.2
    risk_penalties: Mapping[ActionRisk, float] = field(default_factory=lambda: {
        ActionRisk.LOW: 0.0,
        ActionRisk.MEDIUM: 0.08,
        ActionRisk.HIGH: 0.2,
        ActionRisk.CRITICAL: 0.4,
    })

    def __post_init__(self) -> None:
        total = self.confidence_weight + self.evidence_weight + self.urgency_weight
        if round(total, 10) != 1.0:
            raise ValueError("recommendation weights must sum to 1")
        object.__setattr__(
            self,
            "risk_penalties",
            MappingProxyType(dict(self.risk_penalties)),
        )


DEFAULT_RECOMMENDATION_POLICY = RecommendationPolicy()
