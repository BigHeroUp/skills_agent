"""Deterministic engine that manages reusable analytical experience."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.consumption import ConsumerGovernanceMode
from services.knowledge_graph.governance import GOVERNANCE_POLICY_V1, GovernancePolicy
from services.knowledge_graph.store import KnowledgeGraphStore

from .experience_builder import ExperienceBuilder
from .experience_models import AnalyticalExperience, ExperiencePattern, ExperienceRecommendation
from .experience_store import ExperienceStore


PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


class AnalyticalExperienceEngine:
    """Derive, persist, query, and recommend from analytical experience."""

    def __init__(
        self,
        experience_store: ExperienceStore | None = None,
        experience_path: str | None = None,
        query_engine: KnowledgeGraphQueryEngine | None = None,
        kg_store: KnowledgeGraphStore | None = None,
        kg_path: str | None = None,
        governance_mode: ConsumerGovernanceMode | str = ConsumerGovernanceMode.LEGACY,
        governance_policy: GovernancePolicy = GOVERNANCE_POLICY_V1,
    ) -> None:
        self.experience_store = experience_store or ExperienceStore(experience_path)
        self.query_engine = query_engine or KnowledgeGraphQueryEngine(
            store=kg_store or KnowledgeGraphStore(kg_path),
            path=kg_path,
            governance_mode=governance_mode,
            governance_policy=governance_policy,
        )
        self.builder = ExperienceBuilder(
            query_engine=self.query_engine,
            store=getattr(self.query_engine, "store", None),
            path=kg_path,
            governance_mode=governance_mode,
            governance_policy=governance_policy,
        )
        self.experience_store.load()

    def refresh_experience_from_kg(self, limit: int = 20) -> dict[str, Any]:
        try:
            experiences = self.builder.build_from_latest_analyses(limit=max(0, limit))
            self.experience_store.clear()
            for experience in experiences:
                self.experience_store.upsert_experience(experience)
            self.experience_store.save()
        except Exception as exc:
            return {
                "status": "error",
                "experience_count": 0,
                "experience_ids": [],
                "message": f"Impossibile aggiornare l'experience store: {exc}",
                "execution_type": "deterministic_experience_refresh",
            }
        return {
            "status": "ok",
            "experience_count": len(experiences),
            "experience_ids": [experience.id for experience in experiences],
            "execution_type": "deterministic_experience_refresh",
        }

    def find_relevant_experiences(self, current_profile: dict, limit: int = 5) -> dict[str, Any]:
        try:
            normalized = self._normalize_profile(current_profile)
            if not any(normalized.values()):
                return {
                    "execution_type": "deterministic_experience_engine",
                    "status": "insufficient_profile",
                    "message": "Il profilo corrente non contiene segnali sufficienti per cercare esperienze rilevanti.",
                    "experiences": [],
                }

            scored_items: list[dict[str, Any]] = []

            for experience in self.experience_store.list_experiences():
                score, reasons = self._score_experience(experience, normalized)
                if score <= 0:
                    continue
                scored_items.append(
                    {
                        "id": experience.id,
                        "title": experience.title,
                        "description": experience.description,
                        "score": round(min(max(score, 0.0), 1.0), 4),
                        "confidence": experience.confidence,
                        "evidence_count": experience.evidence_count,
                        "metrics": experience.metrics,
                        "columns": experience.columns,
                        "anomalies": experience.anomalies,
                        "root_causes": experience.root_causes,
                        "recommended_steps": experience.recommended_steps,
                        "tags": experience.tags,
                        "reasons": reasons,
                    }
                )

            scored_items.sort(
                key=lambda item: (
                    float(item["score"]),
                    float(item["confidence"]),
                    int(item["evidence_count"]),
                    item["id"],
                ),
                reverse=True,
            )
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "ok",
                "experiences": scored_items[: max(0, limit)],
            }
        except Exception as exc:
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "error",
                "message": f"Errore durante la ricerca esperienze: {exc}",
                "experiences": [],
            }

    def recommend_from_experience(self, current_profile: dict, limit: int = 5) -> dict[str, Any]:
        try:
            relevant = self.find_relevant_experiences(current_profile, limit=max(5, limit * 2))
            aggregated: dict[str, ExperienceRecommendation] = {}

            for item in relevant.get("experiences", []) or []:
                for step in item.get("recommended_steps", []) or []:
                    priority = self._priority_for_step(step)
                    confidence = round(
                        min(
                            1.0,
                            ((float(item.get("score", 0.0)) * 0.6) + (float(item.get("confidence", 0.0)) * 0.4)),
                        ),
                        4,
                    )
                    reason = "; ".join(item.get("reasons") or []) or item.get("description", "")
                    if step not in aggregated:
                        aggregated[step] = ExperienceRecommendation(
                            step=step,
                            reason=reason,
                            priority=priority,
                            confidence=confidence,
                            source_experience_ids=[item["id"]],
                        )
                        continue

                    current = aggregated[step]
                    current.confidence = round(max(current.confidence, confidence), 4)
                    if item["id"] not in current.source_experience_ids:
                        current.source_experience_ids.append(item["id"])
                    if len(reason) > len(current.reason):
                        current.reason = reason
                    if PRIORITY_RANK[priority] < PRIORITY_RANK[current.priority]:
                        current.priority = priority

            recommendations = sorted(
                aggregated.values(),
                key=lambda item: (
                    PRIORITY_RANK.get(item.priority, 99),
                    -float(item.confidence),
                    item.step,
                ),
            )
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "ok",
                "recommendations": [asdict(item) for item in recommendations[: max(0, limit)]],
            }
        except Exception as exc:
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "error",
                "message": f"Errore durante la generazione raccomandazioni: {exc}",
                "recommendations": [],
            }

    def get_experience_summary(self) -> dict[str, Any]:
        try:
            experiences = self.experience_store.list_experiences()
            if not experiences:
                return {
                    "execution_type": "deterministic_experience_engine",
                    "status": "empty",
                    "message": "Nessuna esperienza analitica disponibile nello store locale.",
                    "total_experiences": 0,
                    "top_metrics": [],
                    "top_anomalies": [],
                    "top_root_causes": [],
                    "top_tags": [],
                    "patterns": [],
                }
            metric_counter = Counter()
            anomaly_counter = Counter()
            root_cause_counter = Counter()
            tag_counter = Counter()

            for experience in experiences:
                metric_counter.update(experience.metrics)
                anomaly_counter.update(experience.anomalies)
                root_cause_counter.update(experience.root_causes)
                tag_counter.update(experience.tags)

            patterns = [
                ExperiencePattern(
                    id=f"pattern.metric.{metric}",
                    pattern_type="metric",
                    label=metric,
                    frequency=count,
                    confidence=round(min(1.0, 0.3 + (count * 0.12)), 2),
                    evidence_ids=[experience.id for experience in experiences if metric in experience.metrics],
                    properties={"kind": "metric"},
                )
                for metric, count in metric_counter.most_common(5)
            ]
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "ok",
                "total_experiences": len(experiences),
                "top_metrics": [metric for metric, _ in metric_counter.most_common(5)],
                "top_anomalies": [anomaly for anomaly, _ in anomaly_counter.most_common(5)],
                "top_root_causes": [cause for cause, _ in root_cause_counter.most_common(5)],
                "top_tags": [tag for tag, _ in tag_counter.most_common(5)],
                "patterns": [asdict(pattern) for pattern in patterns],
            }
        except Exception as exc:
            return {
                "execution_type": "deterministic_experience_engine",
                "status": "error",
                "message": f"Errore durante il riepilogo esperienza: {exc}",
                "total_experiences": 0,
                "top_metrics": [],
                "top_anomalies": [],
                "top_root_causes": [],
                "top_tags": [],
                "patterns": [],
            }

    def _normalize_profile(self, current_profile: dict[str, Any]) -> dict[str, set[str]]:
        profile = current_profile if isinstance(current_profile, dict) else {}
        metrics = set(self._normalize_list(profile.get("metrics")))
        if profile.get("primary_metric"):
            metrics.add(str(profile.get("primary_metric")).strip())

        columns = set(self._normalize_list(profile.get("columns")))
        columns.update(self._normalize_list(profile.get("column_names")))
        anomalies = set(self._normalize_list(profile.get("anomalies")))
        root_causes = set(self._normalize_list(profile.get("root_causes")))
        tags = set(self._normalize_list(profile.get("tags")))

        return {
            "metrics": metrics,
            "columns": columns,
            "anomalies": anomalies,
            "root_causes": root_causes,
            "tags": tags,
        }

    def _score_experience(
        self,
        experience: AnalyticalExperience,
        current_profile: dict[str, set[str]],
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0

        metric_match = sorted(current_profile["metrics"] & {item for item in experience.metrics})
        column_match = sorted(current_profile["columns"] & {item for item in experience.columns})
        anomaly_match = sorted(current_profile["anomalies"] & {item for item in experience.anomalies})
        root_cause_match = sorted(current_profile["root_causes"] & {item for item in experience.root_causes})
        tag_match = sorted(current_profile["tags"] & {item for item in experience.tags})

        if metric_match:
            score += 0.35
            reasons.append(f"metriche comuni: {', '.join(metric_match[:3])}")
        if column_match:
            score += 0.2
            reasons.append(f"colonne comuni: {', '.join(column_match[:3])}")
        if anomaly_match:
            score += 0.2
            reasons.append(f"anomalie simili: {', '.join(anomaly_match[:3])}")
        if root_cause_match:
            score += 0.15
            reasons.append(f"root cause simili: {', '.join(root_cause_match[:3])}")
        if tag_match:
            score += 0.1
            reasons.append(f"tag comuni: {', '.join(tag_match[:3])}")

        return score, reasons

    def _priority_for_step(self, step: str) -> str:
        lowered = str(step or "").lower()
        if "verifica infrastrutturale" in lowered:
            return "high"
        if "outlier" in lowered or "segmentazione" in lowered:
            return "medium"
        return "low"

    def _normalize_list(self, values: Any) -> list[str]:
        if isinstance(values, (list, tuple, set)):
            return [str(item).strip() for item in values if str(item).strip()]
        if isinstance(values, str) and values.strip():
            return [values.strip()]
        return []
