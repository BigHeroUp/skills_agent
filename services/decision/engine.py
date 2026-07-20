"""Evidence scoring and deterministic arbitration across analytical options."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .contracts import DecisionEvidence, DecisionOption, DecisionResult, RankedDecision
from .policy import DEFAULT_DECISION_POLICY, DecisionPolicy

if TYPE_CHECKING:
    from services.knowledge_graph.consistency import ConsistencyReport


class DecisionIntelligenceEngine:
    def __init__(self, policy: DecisionPolicy = DEFAULT_DECISION_POLICY):
        self.policy = policy

    def decide(
        self,
        options: tuple[DecisionOption, ...],
        evidence: tuple[DecisionEvidence, ...],
        *,
        consistency_report: "ConsistencyReport | None" = None,
    ) -> DecisionResult:
        if consistency_report is not None and not consistency_report.can_inform_recommendations:
            return self._empty("blocked_by_consistency", options)

        evidence_by_id = {}
        for item in evidence:
            if item.evidence_id in evidence_by_id:
                raise ValueError(f"duplicate decision evidence: {item.evidence_id}")
            evidence_by_id[item.evidence_id] = item

        seen_options = set()
        ranked_values = []
        rejected = []
        for option in options:
            if option.option_id in seen_options:
                raise ValueError(f"duplicate decision option: {option.option_id}")
            seen_options.add(option.option_id)
            present = tuple(item for item in option.evidence_ids if item in evidence_by_id)
            missing = tuple(item for item in option.evidence_ids if item not in evidence_by_id)
            if not present:
                rejected.append(option.option_id)
                continue
            evidence_score = round(
                sum(evidence_by_id[item].score for item in present) / len(present),
                4,
            )
            completeness = len(present) / len(option.evidence_ids) if option.evidence_ids else 0
            adjusted_evidence = evidence_score * completeness
            score = (
                option.base_confidence * self.policy.base_weight
                + adjusted_evidence * self.policy.evidence_weight
                + self.policy.source_priority[option.source] * self.policy.source_weight
                - self.policy.risk_penalty[option.risk]
            )
            score = round(max(0.0, min(score, 1.0)), 4)
            if score < self.policy.minimum_score:
                rejected.append(option.option_id)
                continue
            ranked_values.append((score, evidence_score, option, present, missing))

        ranked_values.sort(key=lambda item: (-item[0], item[2].source.value, item[2].option_id))
        ranked = tuple(
            RankedDecision(
                rank=index,
                option_id=option.option_id,
                action=option.action,
                source=option.source,
                score=score,
                evidence_score=evidence_score,
                evidence_ids=present,
                missing_evidence_ids=missing,
                risk=option.risk,
            )
            for index, (score, evidence_score, option, present, missing)
            in enumerate(ranked_values, start=1)
        )
        return DecisionResult(
            status="selected" if ranked else "abstained",
            selected=ranked[0] if ranked else None,
            ranked_options=ranked,
            rejected_option_ids=tuple(sorted(rejected)),
            policy_id=self.policy.policy_id,
            policy_version=self.policy.version,
        )

    def _empty(self, status, options):
        return DecisionResult(
            status=status,
            selected=None,
            ranked_options=(),
            rejected_option_ids=tuple(sorted(item.option_id for item in options)),
            policy_id=self.policy.policy_id,
            policy_version=self.policy.version,
        )
