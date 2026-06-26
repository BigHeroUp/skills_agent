"""Motore locale per ipotesi di cause radice basate su evidenze."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


class RootCauseAnalysisEngine:
    """Raggruppa segnali gia calcolati e propone cause radice spiegabili."""

    SCHEMA_VERSION = 1
    SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    def analyze(self, context_payload: dict, config: dict | None = None) -> dict:
        """Produce possibili cause radice senza ricalcolare dati o usare OpenAI."""
        payload = context_payload if isinstance(context_payload, dict) else {}
        cfg = config if isinstance(config, dict) else {}
        anomaly_results = payload.get("anomaly_detection_results") or {}
        anomalies = [
            anomaly
            for anomaly in anomaly_results.get("anomalies", []) or []
            if isinstance(anomaly, dict)
        ]
        if not anomalies:
            return self._json_safe({
                "schema_version": self.SCHEMA_VERSION,
                "status": "insufficient_evidence",
                "reason": "Nessuna anomalia disponibile per inferire cause radice supportate da evidenze.",
                "groups": [],
                "possible_causes": [],
                "root_cause_count": 0,
                "reasoning_trace": {
                    "inputs": self._input_summary(payload),
                    "method": "local_evidence_grouping",
                    "stopping_condition": "no_anomalies",
                },
            })

        groups = self.group_related_anomalies(anomalies, cfg)
        causes = self.infer_possible_causes(groups, payload, cfg)
        ranked = self.rank_causes(causes)
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": "computed" if ranked else "insufficient_evidence",
            "reason": None if ranked else "Le anomalie presenti non espongono evidenze sufficienti per formulare cause.",
            "groups": groups,
            "possible_causes": ranked,
            "root_cause_count": len(ranked),
            "reasoning_trace": {
                "inputs": self._input_summary(payload),
                "grouping_rules": [
                    "same_column",
                    "same_or_similar_period",
                    "same_anomaly_type",
                    "compatible_pattern",
                    "similar_severity",
                    "trend_or_degradation_signal",
                ],
                "method": "local_evidence_grouping",
                "domain_pack_used_as_guidance": bool(
                    (payload.get("domain_pack_context") or {}).get("status") == "detected"
                ),
            },
        })

    def group_related_anomalies(
        self,
        anomalies: list[dict],
        config: dict | None = None,
    ) -> list[dict]:
        """Raggruppa anomalie collegate tramite regole locali verificabili."""
        clean = [
            self._normalize_anomaly(anomaly, index)
            for index, anomaly in enumerate(anomalies or [], start=1)
            if isinstance(anomaly, dict)
        ]
        if not clean:
            return []

        visited: set[int] = set()
        groups = []
        for index, anomaly in enumerate(clean):
            if index in visited:
                continue
            stack = [index]
            component = []
            relationship_reasons: list[str] = []
            while stack:
                current_index = stack.pop()
                if current_index in visited:
                    continue
                visited.add(current_index)
                current = clean[current_index]
                component.append(current)
                for other_index, other in enumerate(clean):
                    if other_index in visited or other_index == current_index:
                        continue
                    related, reasons = self._related(current, other)
                    if related:
                        stack.append(other_index)
                        relationship_reasons.extend(reasons)
            groups.append(self._group(component, relationship_reasons))
        groups.sort(key=lambda item: (-self.SEVERITY_ORDER.get(item["severity"], 0), -item["confidence_score"], item["group_id"]))
        return self._json_safe(groups)

    def infer_possible_causes(
        self,
        groups: list[dict],
        context_payload: dict,
        config: dict | None = None,
    ) -> list[dict]:
        """Genera ipotesi di causa solo da gruppi e segnali gia disponibili."""
        payload = context_payload if isinstance(context_payload, dict) else {}
        causes = []
        for group in groups or []:
            if not isinstance(group, dict) or not group.get("anomalies"):
                continue
            evidence = self._supporting_evidence(group, payload)
            if not evidence:
                continue
            cause = {
                "cause_id": self._cause_id(group, evidence),
                "title": self._cause_title(group),
                "description": self._cause_description(group, payload),
                "severity": group.get("severity", "low"),
                "confidence_score": self._cause_confidence(group, evidence),
                "affected_metrics": group.get("affected_metrics", []),
                "related_anomalies": [
                    anomaly.get("anomaly_id")
                    for anomaly in group.get("anomalies", [])
                    if anomaly.get("anomaly_id")
                ],
                "supporting_evidence": evidence,
                "alternative_explanations": self._alternative_explanations(group),
                "recommended_actions": self._recommended_actions(group),
                "method": "local_evidence_grouping",
                "reasoning_trace": {
                    "group_id": group.get("group_id"),
                    "anomaly_types": group.get("anomaly_types", []),
                    "grouping_reasons": group.get("relationship_reasons", []),
                    "domain_guidance": self._domain_guidance(payload),
                    "evidence_count": len(evidence),
                    "hypothesis_boundary": (
                        "La causa e una ipotesi supportata dalle evidenze elencate; "
                        "non viene trattata come prova causale definitiva."
                    ),
                },
            }
            causes.append(cause)
        return self._json_safe(causes)

    def rank_causes(self, causes: list[dict]) -> list[dict]:
        """Ordina cause per severita, confidence e numerosita evidenze."""
        ranked = [
            cause for cause in causes or []
            if isinstance(cause, dict)
        ]
        ranked.sort(
            key=lambda cause: (
                -self.SEVERITY_ORDER.get(cause.get("severity", "low"), 0),
                -float(cause.get("confidence_score", 0) or 0),
                -len(cause.get("supporting_evidence", []) or []),
                cause.get("cause_id", ""),
            )
        )
        return self._json_safe(ranked)

    def export_root_cause_summary(self, results: dict) -> dict:
        """Esporta una sintesi breve per report, sessioni o dashboard."""
        data = results if isinstance(results, dict) else {}
        causes = data.get("possible_causes") or []
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": data.get("status", "unknown"),
            "root_cause_count": len(causes),
            "top_cause_ids": [cause.get("cause_id") for cause in causes[:3]],
            "affected_metrics": self._unique(
                metric
                for cause in causes
                for metric in cause.get("affected_metrics", []) or []
            ),
            "highest_severity": self._highest_severity(
                [cause.get("severity") for cause in causes]
            ),
        })

    def _normalize_anomaly(self, anomaly: dict, index: int) -> dict:
        normalized = dict(anomaly)
        normalized.setdefault("anomaly_id", self._anomaly_id(anomaly, index))
        normalized.setdefault("severity", "low")
        normalized.setdefault("confidence_score", 0.0)
        normalized["period_key"] = self._period_key(
            normalized.get("affected_period")
            or (normalized.get("evidence") or {}).get("period")
        )
        normalized["affected_column"] = str(normalized.get("affected_column") or "").strip()
        normalized["anomaly_type"] = str(normalized.get("anomaly_type") or normalized.get("type") or "unknown")
        return normalized

    def _related(self, left: dict, right: dict) -> tuple[bool, list[str]]:
        reasons = []
        if left.get("affected_column") and left.get("affected_column") == right.get("affected_column"):
            reasons.append("same_column")
        if left.get("period_key") and left.get("period_key") == right.get("period_key"):
            reasons.append("same_or_similar_period")
        if left.get("anomaly_type") == right.get("anomaly_type"):
            reasons.append("same_anomaly_type")
        if self._similar_severity(left.get("severity"), right.get("severity")):
            reasons.append("similar_severity")
        if self._trend_or_degradation(left) and self._trend_or_degradation(right):
            reasons.append("trend_or_degradation_signal")
        return bool(reasons), reasons

    def _group(self, anomalies: list[dict], relationship_reasons: list[str]) -> dict:
        affected_metrics = self._unique(
            anomaly.get("affected_column")
            for anomaly in anomalies
            if anomaly.get("affected_column")
        )
        anomaly_types = self._unique(anomaly.get("anomaly_type") for anomaly in anomalies)
        periods = self._unique(anomaly.get("period_key") for anomaly in anomalies if anomaly.get("period_key"))
        severities = [anomaly.get("severity", "low") for anomaly in anomalies]
        confidence_values = [
            float(anomaly.get("confidence_score", 0) or 0)
            for anomaly in anomalies
            if self._is_number(anomaly.get("confidence_score"))
        ]
        severity = self._highest_severity(severities)
        return {
            "group_id": self._group_id(anomalies),
            "anomaly_count": len(anomalies),
            "severity": severity,
            "confidence_score": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            "affected_metrics": affected_metrics,
            "affected_periods": periods,
            "anomaly_types": anomaly_types,
            "relationship_reasons": self._unique(relationship_reasons),
            "anomalies": anomalies,
        }

    def _supporting_evidence(self, group: dict, payload: dict) -> list[dict]:
        evidence = []
        for anomaly in group.get("anomalies", []) or []:
            item = {
                "type": "anomaly",
                "anomaly_id": anomaly.get("anomaly_id"),
                "anomaly_type": anomaly.get("anomaly_type"),
                "severity": anomaly.get("severity"),
                "affected_metric": anomaly.get("affected_column"),
                "affected_period": anomaly.get("affected_period"),
                "observed_value": anomaly.get("observed_value"),
                "expected_value": anomaly.get("expected_value"),
                "deviation": anomaly.get("deviation"),
                "method": anomaly.get("method"),
                "evidence": anomaly.get("evidence", {}),
            }
            evidence.append(item)

        advanced = payload.get("advanced_statistical_results") or {}
        numeric_analysis = advanced.get("numeric_analysis") or {}
        for metric in group.get("affected_metrics", []) or []:
            stats = numeric_analysis.get(metric)
            if isinstance(stats, dict) and stats.get("status") == "computed":
                evidence.append({
                    "type": "advanced_statistics",
                    "metric": metric,
                    "percentiles": stats.get("percentiles", {}),
                    "dispersion": stats.get("dispersion", {}),
                    "outliers": stats.get("outliers", {}),
                })
        for key, threshold in (advanced.get("threshold_comparisons") or {}).items():
            if isinstance(threshold, dict) and threshold.get("status") == "computed":
                evidence.append({
                    "type": "threshold_comparison",
                    "threshold": key,
                    "breach_rate": threshold.get("breach_rate"),
                    "breach_count": threshold.get("breach_count"),
                })

        strategy = payload.get("analytical_strategy") or {}
        for step in strategy.get("recommended_sequence", []) or []:
            if not isinstance(step, dict):
                continue
            if step.get("analysis_type") in {
                "anomaly_detection",
                "root_cause_analysis",
                "degradation_detection",
                "threshold_comparison",
                "outlier_analysis",
            }:
                evidence.append({
                    "type": "analytical_strategy",
                    "analysis_type": step.get("analysis_type"),
                    "rationale": step.get("rationale"),
                    "confidence_score": step.get("confidence_score"),
                })

        for pattern in payload.get("detected_patterns") or []:
            if isinstance(pattern, dict):
                evidence.append({
                    "type": "pattern",
                    "pattern_id": pattern.get("pattern_id"),
                    "confidence_score": pattern.get("confidence_score"),
                    "matched_keywords": pattern.get("matched_keywords", []),
                })
        return evidence

    def _cause_title(self, group: dict) -> str:
        types = set(group.get("anomaly_types", []))
        metrics = ", ".join(group.get("affected_metrics", []) or ["metrica non specificata"])
        if "performance_degradation" in types:
            return f"Possibile degrado operativo su {metrics}"
        if "sla_violation" in types:
            return f"Possibile superamento sistematico SLA su {metrics}"
        if {"time_series_spike", "sudden_change"}.intersection(types):
            return f"Possibile evento operativo temporaneo su {metrics}"
        if "numeric_outlier" in types:
            return f"Possibile valore estremo su {metrics}"
        return f"Possibile causa comune su {metrics}"

    def _cause_description(self, group: dict, payload: dict) -> str:
        types = ", ".join(group.get("anomaly_types", []))
        metrics = ", ".join(group.get("affected_metrics", []) or ["metriche non specificate"])
        periods = ", ".join(group.get("affected_periods", []) or [])
        suffix = f" nei periodi {periods}" if periods else ""
        domain = self._domain_guidance(payload)
        domain_text = f" Il domain pack suggerisce terminologia/strategie: {domain}." if domain else ""
        return (
            f"Il gruppo contiene {group.get('anomaly_count', 0)} anomalie correlate "
            f"({types}) sulle metriche {metrics}{suffix}. "
            "La causa proposta resta una ipotesi supportata solo dalle evidenze disponibili."
            + domain_text
        )

    def _cause_confidence(self, group: dict, evidence: list[dict]) -> float:
        base = float(group.get("confidence_score", 0) or 0)
        evidence_bonus = min(0.2, max(0, len(evidence) - 1) * 0.03)
        severity_bonus = self.SEVERITY_ORDER.get(group.get("severity", "low"), 1) * 0.03
        return round(max(0.0, min(0.99, base + evidence_bonus + severity_bonus)), 4)

    def _alternative_explanations(self, group: dict) -> list[str]:
        types = set(group.get("anomaly_types", []))
        alternatives = [
            "Errore o incompletezza del dato sorgente.",
            "Evento operativo reale ma isolato.",
        ]
        if {"time_series_spike", "sudden_change", "performance_degradation"}.intersection(types):
            alternatives.append("Cambio di volume, capacita o processo nel periodo osservato.")
        if "sla_violation" in types:
            alternatives.append("Soglia SLA non allineata al perimetro o alla granularita analizzata.")
        if "numeric_outlier" in types:
            alternatives.append("Valore estremo legittimo da trattare come segmento separato.")
        return alternatives

    def _recommended_actions(self, group: dict) -> list[str]:
        actions = []
        for anomaly in group.get("anomalies", []) or []:
            recommendation = anomaly.get("recommendation")
            if recommendation:
                actions.append(str(recommendation))
        actions.extend([
            "Validare le evidenze con owner del processo e fonte dati.",
            "Confrontare la finestra anomala con baseline storica e cambi operativi.",
            "Separare evidence, hypothesis e recommendation prima di decisioni operative.",
        ])
        return self._unique(actions)

    def _domain_guidance(self, payload: dict) -> str:
        context = payload.get("domain_pack_context") or {}
        if not isinstance(context, dict) or context.get("status") != "detected":
            return ""
        suggestion = context.get("suggestion") or {}
        return str(suggestion.get("name") or context.get("pack_id") or "")

    def _input_summary(self, payload: dict) -> dict:
        return {
            "anomaly_count": (payload.get("anomaly_detection_results") or {}).get("anomaly_count", 0),
            "has_advanced_statistics": bool(payload.get("advanced_statistical_results")),
            "has_analytical_strategy": bool(payload.get("analytical_strategy")),
            "detected_pattern_count": len(payload.get("detected_patterns") or []),
            "has_domain_pack": (payload.get("domain_pack_context") or {}).get("status") == "detected",
        }

    def _period_key(self, value: Any) -> str:
        if isinstance(value, dict):
            left = str(value.get("from") or value.get("start") or "")[:7]
            right = str(value.get("to") or value.get("end") or "")[:7]
            return "-".join(item for item in (left, right) if item)
        text = str(value or "")
        match = re.search(r"\d{4}-\d{2}", text)
        return match.group(0) if match else text[:20]

    def _similar_severity(self, left: str, right: str) -> bool:
        return abs(
            self.SEVERITY_ORDER.get(str(left or "low"), 1)
            - self.SEVERITY_ORDER.get(str(right or "low"), 1)
        ) <= 1

    def _trend_or_degradation(self, anomaly: dict) -> bool:
        anomaly_type = str(anomaly.get("anomaly_type") or "")
        return any(term in anomaly_type for term in ("trend", "spike", "change", "degradation", "drift"))

    def _highest_severity(self, severities: list[Any]) -> str:
        values = [str(severity or "low") for severity in severities]
        if not values:
            return "low"
        return max(values, key=lambda item: self.SEVERITY_ORDER.get(item, 1))

    def _group_id(self, anomalies: list[dict]) -> str:
        source = "|".join(sorted(str(anomaly.get("anomaly_id")) for anomaly in anomalies))
        return "rca-group-" + hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]

    def _cause_id(self, group: dict, evidence: list[dict]) -> str:
        source = json.dumps({
            "group_id": group.get("group_id"),
            "evidence": [item.get("type") for item in evidence],
        }, sort_keys=True, default=str)
        return "cause-" + hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]

    def _anomaly_id(self, anomaly: dict, index: int) -> str:
        source = json.dumps(anomaly, sort_keys=True, default=str)
        return "anomaly-" + hashlib.sha1(f"{index}:{source}".encode("utf-8")).hexdigest()[:10]

    def _unique(self, values: Any) -> list:
        output = []
        for value in values:
            if value in (None, "") or value in output:
                continue
            output.append(value)
        return output

    def _is_number(self, value: Any) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    def _json_safe(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
