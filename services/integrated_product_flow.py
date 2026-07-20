"""End-to-end post-analysis product intelligence orchestration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from services.decision import (
    DecisionEvidence,
    DecisionIntelligenceEngine,
    DecisionOption,
    DecisionSource,
    EvidenceKind,
)
from services.experience.experience_engine import AnalyticalExperienceEngine
from services.knowledge_graph.consistency import evaluate_consistency
from services.knowledge_graph.reasoning_engine import build_dataset_profile_from_context
from services.knowledge_graph.validation import validate_graph
from services.narrative import (
    NarrativePolicy,
    NarrativePurpose,
    NarrativeRequest,
    OptionalNarrativeService,
)
from services.production.limits import ProductFlowLimits
from services.production.observability import ProductFlowTelemetry
from services.production.runtime_guard import product_flow_guard
from services.recommendation import (
    ActionRisk,
    NextBestActionEngine,
    RecommendationCandidate,
    RecommendationContext,
)
from utils.context import AgentContext


class IntegratedProductFlow:
    """Connect governance, experience, recommendation, decision, and narrative."""

    def __init__(
        self,
        *,
        kg_path: str | Path,
        experience_path: str | Path | None = None,
        experience_engine: AnalyticalExperienceEngine | None = None,
        recommendation_engine: NextBestActionEngine | None = None,
        decision_engine: DecisionIntelligenceEngine | None = None,
        narrative_service: OptionalNarrativeService | None = None,
        limits: ProductFlowLimits | None = None,
    ) -> None:
        self.kg_path = Path(kg_path)
        self.experience_engine = experience_engine or AnalyticalExperienceEngine(
            experience_path=str(experience_path) if experience_path is not None else None,
            kg_path=str(self.kg_path),
        )
        self.recommendation_engine = recommendation_engine or NextBestActionEngine()
        self.decision_engine = decision_engine or DecisionIntelligenceEngine()
        self.narrative_service = narrative_service
        self.limits = limits or ProductFlowLimits.from_environment()
        self.last_telemetry: ProductFlowTelemetry | None = None

    def run(self, context: AgentContext) -> dict[str, Any]:
        telemetry = ProductFlowTelemetry(
            self._run_id(context),
            stage_timeout_seconds=self.limits.stage_timeout_seconds,
        )
        self.last_telemetry = telemetry
        with product_flow_guard(
            self.kg_path,
            timeout_seconds=self.limits.lock_timeout_seconds,
        ):
            telemetry.run("preflight", self._preflight)
            validation = telemetry.run("structural_validation", lambda: validate_graph(self.kg_path))
            consistency = telemetry.run("semantic_consistency", lambda: evaluate_consistency(validation))
            profile = build_dataset_profile_from_context(context)
            experience_refresh = telemetry.run(
                "experience_refresh",
                lambda: self.experience_engine.refresh_experience_from_kg(
                    limit=self.limits.max_experience_runs,
                    consistency_report=consistency,
                ),
            )
            experience_recommendations = telemetry.run(
                "experience_recommendation",
                lambda: self.experience_engine.recommend_from_experience(
                    profile,
                    limit=min(10, self.limits.max_candidates),
                    consistency_report=consistency,
                ),
            )
            candidates = telemetry.run(
                "candidate_collection",
                lambda: self._collect_candidates(context, experience_recommendations),
            )
            domain = str((context.domain_pack_context or {}).get("pack_id") or "general")
            recommendation_result = telemetry.run(
                "recommendation_ranking",
                lambda: self.recommendation_engine.recommend(
                    candidates,
                    RecommendationContext(
                        domain=domain,
                        context="analysis",
                        maximum_risk=ActionRisk.HIGH,
                    ),
                    consistency_report=consistency,
                    limit=min(5, self.limits.max_candidates),
                ),
            )
            decision_result = telemetry.run(
                "decision_arbitration",
                lambda: self._decide(recommendation_result, candidates, consistency),
            )
            narrative = telemetry.run(
                "narrative",
                lambda: self._narrate(
                    context, consistency, recommendation_result, decision_result
                ),
            )
        return {
            "status": self._status(validation, consistency, decision_result.status),
            "knowledge_graph": {
                "path": str(self.kg_path),
                "validation": validation.report.to_dict(),
            },
            "consistency": consistency.to_dict(),
            "experience": {
                "refresh": experience_refresh,
                "recommendations": experience_recommendations,
            },
            "recommendation": recommendation_result.to_dict(),
            "decision": decision_result.to_dict(),
            "narrative": narrative.to_dict(),
            "execution_type": "integrated_product_intelligence",
            "limits": self.limits.to_dict(),
            "observability": telemetry.to_dict(),
        }

    def _preflight(self) -> None:
        if not self.kg_path.exists():
            raise FileNotFoundError(f"Knowledge graph not found: {self.kg_path}")
        size = self.kg_path.stat().st_size
        if size > self.limits.max_graph_bytes:
            raise ValueError(
                f"Knowledge graph size {size} exceeds product flow limit "
                f"{self.limits.max_graph_bytes}"
            )

    @staticmethod
    def _run_id(context: AgentContext) -> str:
        material = "|".join((
            str(getattr(context, "created_at", "")),
            str(getattr(context, "user_input", "")),
            str((context.metadata or {}).get("dataset_name") or ""),
        ))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def _collect_candidates(self, context, experience_payload):
        candidates = list(
            self.recommendation_engine.candidates_from_experience(experience_payload)
        )
        for item in context.recommended_analytical_steps or []:
            if isinstance(item, dict):
                action = str(item.get("step") or "").strip()
                reason = str(item.get("reason") or "Deterministic knowledge reasoning.")
                priority = str(item.get("priority") or "medium")
                confidence = self._bounded(item.get("confidence"), 0.65)
                source = str(item.get("source") or "strategy")
            else:
                action = str(item).strip()
                reason, priority, confidence, source = (
                    "Deterministic knowledge reasoning.", "medium", 0.65, "strategy"
                )
            self._append_candidate(candidates, action, reason, priority, confidence, source)

        for action in context.autonomous_recommendations or []:
            self._append_candidate(
                candidates,
                str(action).strip(),
                "Deterministic autonomous analysis.",
                "medium",
                0.6,
                "strategy",
            )

        anomalies = (context.anomaly_detection_results or {}).get("anomalies") or []
        for anomaly in anomalies:
            if not isinstance(anomaly, dict):
                continue
            label = anomaly.get("anomaly_type") or anomaly.get("anomaly_id") or "anomaly"
            column = anomaly.get("affected_column") or "metric"
            severity = str(anomaly.get("severity") or "medium").lower()
            self._append_candidate(
                candidates,
                f"Validate anomaly {label} on {column}",
                "An anomaly was detected by the deterministic engine.",
                "high" if severity in {"high", "critical"} else "medium",
                self._bounded(anomaly.get("confidence"), 0.72),
                "anomaly",
                risk=ActionRisk.MEDIUM,
            )

        causes = (context.root_cause_results or {}).get("possible_causes") or []
        for cause in causes:
            if not isinstance(cause, dict):
                continue
            title = str(cause.get("title") or cause.get("cause_id") or "root cause").strip()
            self._append_candidate(
                candidates,
                f"Investigate root cause: {title}",
                "A deterministic root-cause hypothesis requires evidence verification.",
                "high",
                self._bounded(cause.get("confidence"), 0.68),
                "root_cause",
                risk=ActionRisk.MEDIUM,
            )
        unique = {item.candidate_id: item for item in candidates if item.action}
        ordered = tuple(unique[key] for key in sorted(unique))
        return ordered[: self.limits.max_candidates]

    def _append_candidate(
        self,
        candidates,
        action,
        reason,
        priority,
        confidence,
        source,
        risk=ActionRisk.LOW,
    ):
        if not action:
            return
        identifier = hashlib.sha256(f"{source}|{action}".encode("utf-8")).hexdigest()[:16]
        candidates.append(RecommendationCandidate(
            candidate_id=f"{source}:{identifier}",
            action=action,
            reason=reason,
            confidence=confidence,
            evidence_strength=confidence,
            urgency={"high": 0.9, "medium": 0.55, "low": 0.25}.get(priority, 0.55),
            risk=risk,
            evidence_ids=(f"evidence:{source}:{identifier}",),
            source=source,
        ))

    def _decide(self, recommendation_result, candidates, consistency):
        candidates_by_id = {item.candidate_id: item for item in candidates}
        evidence_by_id = {}
        options = []
        for ranked in recommendation_result.recommendations:
            candidate = candidates_by_id[ranked.candidate_id]
            evidence_ids = ranked.evidence_ids or (f"evidence:{ranked.candidate_id}",)
            for evidence_id in evidence_ids:
                evidence_by_id.setdefault(evidence_id, DecisionEvidence(
                    evidence_id=evidence_id,
                    kind=self._evidence_kind(candidate.source),
                    strength=ranked.score,
                    reliability=candidate.evidence_strength,
                    confidence=ranked.confidence,
                    summary=ranked.reason,
                ))
            options.append(DecisionOption(
                option_id=ranked.candidate_id,
                action=ranked.action,
                source=self._decision_source(candidate.source),
                base_confidence=ranked.confidence,
                evidence_ids=tuple(evidence_ids),
                risk=ranked.risk,
            ))
        return self.decision_engine.decide(
            tuple(options),
            tuple(evidence_by_id[key] for key in sorted(evidence_by_id)),
            consistency_report=consistency,
        )

    def _narrate(self, context, consistency, recommendation_result, decision_result):
        enabled = bool((context.metadata or {}).get("enable_narrative", False))
        service = self.narrative_service or OptionalNarrativeService(
            policy=NarrativePolicy(enabled=enabled)
        )
        deterministic_text = context.final_report.strip() or self._decision_summary(decision_result)
        return service.render(NarrativeRequest(
            purpose=NarrativePurpose.EXECUTIVE_SUMMARY,
            deterministic_text=deterministic_text,
            facts={
                "consistency_status": consistency.status.value,
                "decision_status": decision_result.status,
                "recommendation_count": len(recommendation_result.recommendations),
                "selected_option_id": (
                    decision_result.selected.option_id if decision_result.selected else None
                ),
            },
            audience="business",
            language=str((context.metadata or {}).get("language") or "it"),
        ))

    @staticmethod
    def _decision_summary(result):
        if result.selected:
            return f"Selected analytical action: {result.selected.action}"
        return "No analytical action was selected because evidence was insufficient."

    @staticmethod
    def _status(validation, consistency, decision_status):
        if not validation.can_consume:
            return "blocked_by_governance"
        if not consistency.can_inform_recommendations:
            return "blocked_by_consistency"
        if decision_status == "selected":
            return "completed"
        return "completed_without_decision"

    @staticmethod
    def _bounded(value, default):
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _decision_source(source):
        return {
            "strategy": DecisionSource.STRATEGY,
            "anomaly": DecisionSource.ANOMALY,
            "root_cause": DecisionSource.ROOT_CAUSE,
        }.get(source, DecisionSource.RECOMMENDATION)

    @staticmethod
    def _evidence_kind(source):
        return {
            "anomaly": EvidenceKind.ANOMALY,
            "root_cause": EvidenceKind.ROOT_CAUSE,
            "experience": EvidenceKind.EXPERIENCE,
        }.get(source, EvidenceKind.POLICY)
