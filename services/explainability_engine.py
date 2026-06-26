"""Motore locale per rendere spiegabili analisi, conclusioni e raccomandazioni."""

from __future__ import annotations

import json
import math
from typing import Any


class ExplainabilityEngine:
    """Costruisce spiegazioni strutturate senza chiamate a servizi esterni."""

    SCHEMA_VERSION = 1

    def explain_analysis(
        self,
        processed_data: dict,
        analysis: dict | None = None,
        user_request: str = "",
    ) -> dict:
        """Produce una spiegazione JSON-safe della pipeline analitica."""
        data = processed_data if isinstance(processed_data, dict) else {}
        result = analysis if isinstance(analysis, dict) else {}
        strategy = data.get("analytical_strategy") or result.get("analytical_strategy") or {}
        patterns = data.get("detected_patterns") or result.get("detected_patterns") or []
        advanced_stats = (
            data.get("advanced_statistical_results")
            or result.get("advanced_statistical_results")
            or {}
        )
        anomaly_results = (
            data.get("anomaly_detection_results")
            or result.get("anomaly_detection_results")
            or {}
        )
        learning_state = data.get("learning_state") or result.get("learning_state") or {}

        explanation = {
            "schema_version": self.SCHEMA_VERSION,
            "user_request": user_request or result.get("user_request") or "",
            "reasoning_path": self._reasoning_path(data, result, strategy),
            "analytical_strategy": self._json_safe(strategy),
            "engines_used": self._engines_used(data, result),
            "patterns_applied": self._patterns_applied(patterns, data),
            "statistics_used": self._statistics_used(data, advanced_stats),
            "anomalies_detected": self._anomalies_detected(result, anomaly_results),
            "confidence_score": self._confidence_score(
                strategy,
                patterns,
                learning_state,
                anomaly_results,
            ),
            "confidence_factors": self._confidence_factors(
                strategy,
                patterns,
                learning_state,
                anomaly_results,
            ),
            "evidence": self._evidence(result),
            "conclusions": self._conclusions(result),
            "recommendations": self._recommendations(result, anomaly_results),
            "algorithms_used": self._algorithms_used(data, result, advanced_stats, anomaly_results),
            "recommendation_reasoning": self._recommendation_reasoning(result, anomaly_results),
        }
        return self._json_safe(explanation)

    def format_for_report(self, explanation: dict) -> str:
        """Formatta la spiegazione per la sezione Markdown del report finale."""
        data = explanation if isinstance(explanation, dict) else {}
        lines = [
            "### Decision Flow",
            self._format_items(
                [
                    item.get("summary", str(item))
                    for item in data.get("reasoning_path", [])
                    if isinstance(item, dict)
                ],
                "Decision flow non disponibile.",
            ),
            "",
            "### Evidence",
            self._format_items(
                [
                    item.get("summary", str(item))
                    for item in data.get("evidence", [])
                    if isinstance(item, dict)
                ],
                "Evidenze non disponibili.",
            ),
            "",
            "### Confidence",
            f"- Score complessivo: {self._fmt(data.get('confidence_score', 0))}",
            self._format_items(
                [
                    item.get("summary", str(item))
                    for item in data.get("confidence_factors", [])
                    if isinstance(item, dict)
                ],
                "Fattori di confidence non disponibili.",
            ),
            "",
            "### Algorithms Used",
            self._format_items(
                [
                    item.get("name", str(item))
                    + (f": {item.get('reason')}" if item.get("reason") else "")
                    for item in data.get("algorithms_used", [])
                    if isinstance(item, dict)
                ],
                "Algoritmi non disponibili.",
            ),
            "",
            "### Pattern Used",
            self._format_items(
                [
                    item.get("pattern_id", str(item))
                    + (f": {item.get('reason')}" if item.get("reason") else "")
                    for item in data.get("patterns_applied", [])
                    if isinstance(item, dict)
                ],
                "Nessun pattern applicato.",
            ),
            "",
            "### Recommendation Reasoning",
            self._format_items(
                [
                    item.get("summary", str(item))
                    for item in data.get("recommendation_reasoning", [])
                    if isinstance(item, dict)
                ],
                "Ragionamento raccomandazioni non disponibile.",
            ),
        ]
        return "\n".join(lines)

    def _reasoning_path(self, data: dict, analysis: dict, strategy: dict) -> list[dict]:
        path = []
        execution = data.get("execution_summary") or analysis.get("execution_summary") or {}
        plan = data.get("analysis_plan") or analysis.get("analysis_plan") or {}
        if plan:
            path.append({
                "step": "analysis_plan",
                "summary": (
                    "Il sistema ha costruito un piano analitico "
                    f"{plan.get('analysis_type', 'deterministico')}."
                ),
                "source": data.get("plan_source", "local"),
            })
        if strategy:
            path.append({
                "step": "analytical_strategy",
                "summary": (
                    "L'Analytical Reasoning Layer ha ordinato "
                    f"{len(strategy.get('recommended_sequence') or [])} analisi candidate "
                    "e identificato eventuali esclusioni o chiarimenti."
                ),
                "strategy_id": strategy.get("strategy_id"),
            })
        if execution:
            path.append({
                "step": "execution",
                "summary": (
                    "L'esecuzione locale risulta "
                    f"{execution.get('status', 'non specificata')} "
                    f"tramite {execution.get('source', 'motore locale')}."
                ),
                "status": execution.get("status"),
            })
        if analysis.get("executive_summary"):
            path.append({
                "step": "senior_analysis",
                "summary": "Il Senior Data Analyst Engine ha trasformato risultati calcolati in conclusioni e raccomandazioni.",
            })
        return path

    def _engines_used(self, data: dict, analysis: dict) -> list[dict]:
        engines = []
        if data.get("analysis_plan") or data.get("deterministic_results"):
            engines.append(self._engine("AnalysisEngine", "Piano e risultati deterministici Pandas."))
        if data.get("analytical_strategy") or analysis.get("analytical_strategy"):
            engines.append(self._engine("AnalyticalReasoningLayer", "Strategia, ranking, esclusioni e chiarimenti."))
        if data.get("advanced_statistical_results") or analysis.get("advanced_statistical_results"):
            engines.append(self._engine("AdvancedStatisticalEngine", "Percentili, dispersione, correlazioni, soglie e completezza."))
        if data.get("anomaly_detection_results") or analysis.get("anomaly_detection_results"):
            engines.append(self._engine("AnomalyDetectionEngine", "Outlier, spike, degrado, drift e SLA."))
        if data.get("learning_state") or analysis.get("learning_state"):
            engines.append(self._engine("LearningEngine", "Confidence, eventi e affidabilita dei pattern."))
        if data.get("detected_patterns") or analysis.get("detected_patterns"):
            engines.append(self._engine("PatternKnowledgeEngine", "Pattern analitici e best practice."))
        if analysis:
            engines.append(self._engine("SeniorDataAnalystEngine", "Sintesi, KPI, conclusioni e report."))
        return engines

    def _patterns_applied(self, patterns: list, data: dict) -> list[dict]:
        output = []
        for pattern in patterns or []:
            if not isinstance(pattern, dict):
                continue
            output.append({
                "pattern_id": pattern.get("pattern_id"),
                "name": pattern.get("name"),
                "confidence_score": pattern.get("confidence_score"),
                "matched_keywords": pattern.get("matched_keywords", []),
                "reason": "Pattern rilevato da richiesta utente, metadata o domain pack.",
            })
        domain = data.get("domain_pack_context") or {}
        if isinstance(domain, dict) and domain.get("status") == "detected":
            output.append({
                "pattern_id": f"domain_pack:{domain.get('pack_id')}",
                "name": (domain.get("suggestion") or {}).get("name", domain.get("pack_id")),
                "confidence_score": (domain.get("suggestion") or {}).get("confidence_score"),
                "matched_keywords": (domain.get("suggestion") or {}).get("matched_terms", []),
                "reason": "Domain Intelligence Pack riconosciuto e usato come conoscenza specialistica.",
            })
        return output

    def _statistics_used(self, data: dict, advanced_stats: dict) -> list[dict]:
        output = []
        summary = data.get("deterministic_summary") or {}
        for column, stats in list((summary.get("numeric_summary") or {}).items())[:8]:
            output.append({
                "source": "deterministic_summary",
                "column": column,
                "statistics": [
                    key for key in ("count", "sum", "mean", "median", "min", "max", "std")
                    if stats.get(key) is not None
                ],
            })
        for column, item in list((advanced_stats.get("numeric_analysis") or {}).items())[:8]:
            if not isinstance(item, dict) or item.get("status") != "computed":
                continue
            output.append({
                "source": "advanced_statistical_results",
                "column": column,
                "statistics": [
                    "percentiles",
                    "dispersion",
                    "outliers",
                ],
            })
        if advanced_stats.get("correlation_matrices"):
            output.append({
                "source": "advanced_statistical_results",
                "statistics": ["correlation_matrices"],
            })
        if advanced_stats.get("threshold_comparisons"):
            output.append({
                "source": "advanced_statistical_results",
                "statistics": ["threshold_comparisons"],
            })
        return output

    def _anomalies_detected(self, analysis: dict, anomaly_results: dict) -> list[dict]:
        output = []
        for item in anomaly_results.get("anomalies") or []:
            if isinstance(item, dict):
                output.append({
                    "source": "AnomalyDetectionEngine",
                    "anomaly_type": item.get("anomaly_type"),
                    "severity": item.get("severity"),
                    "confidence_score": item.get("confidence_score"),
                    "affected_column": item.get("affected_column"),
                    "evidence": item.get("evidence", {}),
                    "recommendation": item.get("recommendation"),
                })
        for item in analysis.get("anomaly_analysis") or []:
            if isinstance(item, dict):
                output.append({
                    "source": "SeniorDataAnalystEngine",
                    "anomaly_type": item.get("type"),
                    "severity": item.get("severity"),
                    "summary": item.get("summary"),
                })
        return output

    def _confidence_score(
        self,
        strategy: dict,
        patterns: list,
        learning_state: dict,
        anomaly_results: dict,
    ) -> float:
        values = []
        if self._is_number(strategy.get("confidence_score")):
            values.append(float(strategy["confidence_score"]))
        for pattern in patterns or []:
            if isinstance(pattern, dict) and self._is_number(pattern.get("confidence_score")):
                values.append(float(pattern["confidence_score"]))
        if self._is_number(learning_state.get("average_confidence")):
            values.append(float(learning_state["average_confidence"]))
        anomaly_confidences = [
            float(item["confidence_score"])
            for item in anomaly_results.get("anomalies", []) or []
            if isinstance(item, dict) and self._is_number(item.get("confidence_score"))
        ]
        if anomaly_confidences:
            values.append(sum(anomaly_confidences) / len(anomaly_confidences))
        if not values:
            return 0.0
        return round(max(0.0, min(1.0, sum(values) / len(values))), 4)

    def _confidence_factors(
        self,
        strategy: dict,
        patterns: list,
        learning_state: dict,
        anomaly_results: dict,
    ) -> list[dict]:
        factors = []
        if strategy:
            factors.append({
                "factor": "analytical_strategy",
                "score": strategy.get("confidence_score", 0),
                "summary": f"Strategia locale con confidence {strategy.get('confidence_score', 0)}.",
            })
        if patterns:
            factors.append({
                "factor": "patterns",
                "score": self._average(
                    [
                        item.get("confidence_score")
                        for item in patterns
                        if isinstance(item, dict)
                    ]
                ),
                "summary": f"{len(patterns)} pattern hanno contribuito alla spiegazione.",
            })
        if learning_state:
            factors.append({
                "factor": "learning_state",
                "score": learning_state.get("average_confidence", 0),
                "summary": "Learning Engine usato per affidabilita e audit trail dei pattern.",
            })
        anomalies = anomaly_results.get("anomalies") or []
        if anomalies:
            factors.append({
                "factor": "anomaly_detection",
                "score": self._average(
                    [
                        item.get("confidence_score")
                        for item in anomalies
                        if isinstance(item, dict)
                    ]
                ),
                "summary": f"{len(anomalies)} anomalie hanno confidence esplicita.",
            })
        return factors

    def _evidence(self, analysis: dict) -> list[dict]:
        evidence = []
        for finding in analysis.get("key_findings") or []:
            evidence.append({"type": "key_finding", "summary": str(finding)})
        for kpi in analysis.get("kpi_summary") or []:
            if isinstance(kpi, dict):
                evidence.append({
                    "type": "kpi",
                    "summary": f"{kpi.get('name')}: {kpi.get('value')}",
                    "value": kpi.get("value"),
                })
        for trend in analysis.get("trend_analysis") or []:
            if isinstance(trend, dict):
                evidence.append({"type": "trend", "summary": trend.get("summary", "")})
        for anomaly in analysis.get("anomaly_analysis") or []:
            if isinstance(anomaly, dict):
                evidence.append({"type": "anomaly", "summary": anomaly.get("summary", "")})
        return [item for item in evidence if item.get("summary")]

    def _conclusions(self, analysis: dict) -> list[dict]:
        conclusions = []
        if analysis.get("executive_summary"):
            conclusions.append({
                "type": "executive_summary",
                "summary": analysis["executive_summary"],
            })
        for finding in analysis.get("key_findings") or []:
            conclusions.append({"type": "finding", "summary": str(finding)})
        return conclusions

    def _recommendations(self, analysis: dict, anomaly_results: dict) -> list[dict]:
        recommendations = [
            {"source": "SeniorDataAnalystEngine", "recommendation": str(item)}
            for item in analysis.get("operational_recommendations") or []
        ]
        for anomaly in anomaly_results.get("anomalies") or []:
            if isinstance(anomaly, dict) and anomaly.get("recommendation"):
                recommendations.append({
                    "source": "AnomalyDetectionEngine",
                    "recommendation": anomaly["recommendation"],
                    "anomaly_type": anomaly.get("anomaly_type"),
                })
        return recommendations

    def _algorithms_used(
        self,
        data: dict,
        analysis: dict,
        advanced_stats: dict,
        anomaly_results: dict,
    ) -> list[dict]:
        algorithms = []
        if data.get("deterministic_summary"):
            algorithms.append({"name": "Pandas deterministic profiling", "reason": "Profilo dataset, tipi, null, duplicati e riepiloghi numerici."})
        if data.get("deterministic_results"):
            result = data["deterministic_results"]
            algorithms.append({"name": result.get("analysis_type", "deterministic_analysis"), "reason": "Analisi deterministica principale."})
        if advanced_stats.get("numeric_analysis"):
            algorithms.append({"name": "percentile_and_dispersion_analysis", "reason": "Percentili, IQR, MAD, deviazione standard e outlier."})
        if advanced_stats.get("correlation_matrices"):
            algorithms.append({"name": "correlation_matrix", "reason": "Pearson, Spearman o Kendall quando disponibili."})
        if advanced_stats.get("threshold_comparisons"):
            algorithms.append({"name": "threshold_comparison", "reason": "Confronto locale con soglie o SLA."})
        if anomaly_results.get("anomalies"):
            algorithms.append({"name": "explainable_anomaly_detection", "reason": "Severity, confidence, evidenza e raccomandazione per ogni anomalia."})
        if analysis.get("analytical_strategy"):
            algorithms.append({"name": "local_strategy_ranking", "reason": "Ranking locale di analisi candidate e stopping conditions."})
        return algorithms

    def _recommendation_reasoning(self, analysis: dict, anomaly_results: dict) -> list[dict]:
        output = []
        for recommendation in analysis.get("operational_recommendations") or []:
            output.append({
                "source": "SeniorDataAnalystEngine",
                "summary": (
                    f"Raccomandazione: {recommendation} "
                    "Deriva da KPI, trend, anomalie o note di qualita calcolate localmente."
                ),
            })
        for anomaly in anomaly_results.get("anomalies") or []:
            if isinstance(anomaly, dict) and anomaly.get("recommendation"):
                output.append({
                    "source": "AnomalyDetectionEngine",
                    "summary": (
                        f"{anomaly.get('recommendation')} "
                        f"Motivo: {anomaly.get('anomaly_type')} con severity "
                        f"{anomaly.get('severity')} e confidence "
                        f"{anomaly.get('confidence_score')}."
                    ),
                })
        return output

    def _engine(self, name: str, reason: str) -> dict:
        return {"name": name, "reason": reason}

    def _format_items(self, items: list[str], empty: str) -> str:
        clean_items = [item for item in items if item]
        if not clean_items:
            return f"- {empty}"
        return "\n".join(f"- {item}" for item in clean_items)

    def _average(self, values: list[Any]) -> float:
        numbers = [float(value) for value in values if self._is_number(value)]
        if not numbers:
            return 0.0
        return round(sum(numbers) / len(numbers), 4)

    def _fmt(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value)

    def _is_number(self, value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    def _json_safe(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
