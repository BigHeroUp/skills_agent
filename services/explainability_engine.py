"""Motore locale per spiegazioni strutturate e JSON-safe."""

from __future__ import annotations

import json
import math
from typing import Any


class ExplainabilityEngine:
    """Costruisce spiegazioni locali senza chiamate a servizi AI esterni."""

    SCHEMA_VERSION = 1

    def explain_analysis(
        self,
        processed_data: dict,
        analysis: dict | None = None,
        user_request: str = "",
    ) -> dict:
        """Restituisce reasoning path, evidenze e conclusioni in forma serializzabile."""
        data = processed_data if isinstance(processed_data, dict) else {}
        report_analysis = analysis if isinstance(analysis, dict) else {}
        root_cause_results = (
            data.get("root_cause_results")
            or report_analysis.get("root_cause_results")
            or {}
        )
        anomaly_results = data.get("anomaly_detection_results") or {}
        statistical_results = data.get("advanced_statistical_results") or {}
        strategy = data.get("analytical_strategy") or {}
        patterns = data.get("detected_patterns") or []

        reasoning_path = [
            {
                "step": "analytical_strategy",
                "summary": "Strategia locale costruita da richiesta, metadata e pattern disponibili.",
                "evidence_refs": [
                    step.get("analysis_type")
                    for step in strategy.get("recommended_sequence", [])[:8]
                    if isinstance(step, dict)
                ],
            },
            {
                "step": "advanced_statistics",
                "summary": "Statistiche avanzate usate come evidenza quantitativa quando disponibili.",
                "status": statistical_results.get("status", "available" if statistical_results else "missing"),
            },
            {
                "step": "anomaly_detection",
                "summary": "Anomalie locali considerate come segnali, non come prova causale definitiva.",
                "anomaly_count": anomaly_results.get("anomaly_count", 0),
            },
        ]
        if root_cause_results:
            reasoning_path.append({
                "step": "root_cause_analysis",
                "summary": "Cause radice inferite solo da evidenze già presenti nel payload.",
                "status": root_cause_results.get("status"),
                "root_cause_count": root_cause_results.get("root_cause_count", 0),
            })

        evidence = self._collect_evidence(
            anomaly_results,
            statistical_results,
            root_cause_results,
        )
        confidence = self._confidence(root_cause_results, anomaly_results, strategy)
        explanation = {
            "schema_version": self.SCHEMA_VERSION,
            "user_request": str(user_request or data.get("user_request") or ""),
            "reasoning_path": reasoning_path,
            "analytical_strategy": strategy,
            "engines_used": self._engines_used(data, root_cause_results),
            "patterns_applied": patterns,
            "statistics_used": statistical_results,
            "anomalies_detected": anomaly_results,
            "root_cause_results": root_cause_results,
            "confidence_score": confidence,
            "evidence": evidence,
            "conclusions": self._conclusions(root_cause_results, anomaly_results),
            "recommendations": self._recommendations(root_cause_results),
        }
        return self._json_safe(explanation)

    def _collect_evidence(
        self,
        anomaly_results: dict,
        statistical_results: dict,
        root_cause_results: dict,
    ) -> list[dict]:
        evidence = []
        for anomaly in (anomaly_results.get("anomalies") or [])[:10]:
            if isinstance(anomaly, dict):
                evidence.append({
                    "source": "anomaly_detection",
                    "type": anomaly.get("anomaly_type"),
                    "severity": anomaly.get("severity"),
                    "affected_metric": anomaly.get("affected_column"),
                    "confidence_score": anomaly.get("confidence_score"),
                })
        for column, stats in list((statistical_results.get("numeric_analysis") or {}).items())[:8]:
            if isinstance(stats, dict) and stats.get("status") == "computed":
                evidence.append({
                    "source": "advanced_statistical_engine",
                    "metric": column,
                    "percentiles": stats.get("percentiles", {}),
                    "outliers": stats.get("outliers", {}),
                })
        for cause in (root_cause_results.get("possible_causes") or [])[:5]:
            if not isinstance(cause, dict):
                continue
            evidence.append({
                "source": "root_cause_analysis_engine",
                "cause_id": cause.get("cause_id"),
                "title": cause.get("title"),
                "severity": cause.get("severity"),
                "confidence_score": cause.get("confidence_score"),
                "supporting_evidence_count": len(cause.get("supporting_evidence") or []),
            })
        return evidence

    def _engines_used(self, data: dict, root_cause_results: dict) -> list[str]:
        engines = ["AnalyticalReasoningLayer"]
        if data.get("advanced_statistical_results"):
            engines.append("AdvancedStatisticalEngine")
        if data.get("anomaly_detection_results"):
            engines.append("AnomalyDetectionEngine")
        if data.get("learning_state"):
            engines.append("LearningEngine")
        if data.get("detected_patterns"):
            engines.append("PatternKnowledgeEngine")
        if root_cause_results:
            engines.append("RootCauseAnalysisEngine")
        return engines

    def _confidence(self, root_cause_results: dict, anomaly_results: dict, strategy: dict) -> float:
        causes = root_cause_results.get("possible_causes") or []
        if causes:
            values = [
                float(cause.get("confidence_score", 0) or 0)
                for cause in causes
                if isinstance(cause, dict)
            ]
            if values:
                return round(sum(values) / len(values), 4)
        if anomaly_results.get("anomaly_count"):
            return round(float(strategy.get("confidence_score", 0.45) or 0.45), 4)
        return 0.0

    def _conclusions(self, root_cause_results: dict, anomaly_results: dict) -> list[str]:
        causes = root_cause_results.get("possible_causes") or []
        if causes:
            return [
                f"{cause.get('title')} supportata da {len(cause.get('supporting_evidence') or [])} evidenze."
                for cause in causes[:5]
                if isinstance(cause, dict)
            ]
        if anomaly_results.get("anomaly_count"):
            return ["Sono presenti anomalie, ma non ci sono evidenze sufficienti per cause radice robuste."]
        return ["Nessuna anomalia disponibile per spiegazioni causali locali."]

    def _recommendations(self, root_cause_results: dict) -> list[str]:
        output = []
        for cause in (root_cause_results.get("possible_causes") or [])[:5]:
            if isinstance(cause, dict):
                output.extend(cause.get("recommended_actions") or [])
        return list(dict.fromkeys(output))

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)
