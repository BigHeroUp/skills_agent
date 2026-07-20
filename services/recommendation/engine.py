"""Explainable deterministic next-best-action engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contracts import (
    RISK_RANK,
    RecommendationCandidate,
    RecommendationContext,
    RecommendationResult,
    RankedRecommendation,
)
from .policy import DEFAULT_RECOMMENDATION_POLICY, RecommendationPolicy

if TYPE_CHECKING:
    from services.knowledge_graph.consistency import ConsistencyReport


class NextBestActionEngine:
    def __init__(self, policy: RecommendationPolicy = DEFAULT_RECOMMENDATION_POLICY):
        self.policy = policy

    def recommend(
        self,
        candidates: tuple[RecommendationCandidate, ...],
        context: RecommendationContext,
        *,
        consistency_report: "ConsistencyReport | None" = None,
        limit: int = 5,
    ) -> RecommendationResult:
        if consistency_report is not None and not consistency_report.can_inform_recommendations:
            return RecommendationResult(
                status="blocked_by_consistency",
                recommendations=(),
                rejected_candidate_ids=tuple(sorted(item.candidate_id for item in candidates)),
                policy_id=self.policy.policy_id,
                policy_version=self.policy.version,
            )

        accepted: list[tuple[float, RecommendationCandidate]] = []
        rejected: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.candidate_id in seen:
                raise ValueError(f"duplicate recommendation candidate: {candidate.candidate_id}")
            seen.add(candidate.candidate_id)
            if not self._is_admissible(candidate, context):
                rejected.append(candidate.candidate_id)
                continue
            score = (
                candidate.confidence * self.policy.confidence_weight
                + candidate.evidence_strength * self.policy.evidence_weight
                + candidate.urgency * self.policy.urgency_weight
                - self.policy.risk_penalties.get(candidate.risk, 0.0)
            )
            accepted.append((round(max(0.0, min(score, 1.0)), 4), candidate))

        accepted.sort(key=lambda item: (-item[0], item[1].risk.value, item[1].candidate_id))
        ranked = tuple(
            RankedRecommendation(
                rank=index,
                candidate_id=candidate.candidate_id,
                action=candidate.action,
                reason=candidate.reason,
                priority=self._priority(score),
                score=score,
                confidence=candidate.confidence,
                risk=candidate.risk,
                evidence_ids=candidate.evidence_ids,
                source=candidate.source,
            )
            for index, (score, candidate) in enumerate(accepted[:max(0, limit)], start=1)
        )
        return RecommendationResult(
            status="ok" if ranked else "no_admissible_actions",
            recommendations=ranked,
            rejected_candidate_ids=tuple(sorted(rejected)),
            policy_id=self.policy.policy_id,
            policy_version=self.policy.version,
        )

    @staticmethod
    def candidates_from_experience(payload: dict[str, Any]) -> tuple[RecommendationCandidate, ...]:
        candidates = []
        for index, item in enumerate(payload.get("recommendations") or []):
            confidence = float(item.get("confidence", 0.0) or 0.0)
            candidates.append(RecommendationCandidate(
                candidate_id=str(item.get("candidate_id") or f"experience:{index}"),
                action=str(item.get("step") or "").strip(),
                reason=str(item.get("reason") or "Evidence from analytical experience."),
                confidence=max(0.0, min(confidence, 1.0)),
                evidence_strength=max(0.0, min(confidence, 1.0)),
                urgency={"high": 0.9, "medium": 0.5, "low": 0.2}.get(
                    str(item.get("priority") or "low"), 0.2
                ),
                evidence_ids=tuple(item.get("source_experience_ids") or ()),
                source="experience",
            ))
        return tuple(candidates)

    @staticmethod
    def _priority(score: float) -> str:
        if score >= 0.7:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    @staticmethod
    def _is_admissible(candidate: RecommendationCandidate, context: RecommendationContext) -> bool:
        if candidate.confidence < context.minimum_confidence:
            return False
        if RISK_RANK[candidate.risk] > RISK_RANK[context.maximum_risk]:
            return False
        if candidate.domain not in {"general", context.domain}:
            return False
        if candidate.contexts and context.context not in candidate.contexts:
            return False
        return True
