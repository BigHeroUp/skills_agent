"""Core deterministic consistency rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from services.knowledge_graph.domain import GraphIssue, IssueSeverity

from .contracts import ConsistencyContext


def _issue(rule, code, severity, location, message, evidence, suggestion):
    return GraphIssue(
        code=code,
        severity=severity,
        category="knowledge_consistency",
        location=location,
        message=message,
        evidence=evidence,
        suggestion=suggestion,
        rule_id=rule.rule_id,
        rule_version=rule.version,
    )


class ConfidenceRangeRule:
    rule_id = "core.consistency.confidence_range"
    version = "1.0.0"
    PROPERTY_NAMES = ("confidence", "confidence_score")

    def evaluate(self, context: ConsistencyContext) -> tuple[GraphIssue, ...]:
        issues = []
        for kind, records in (("nodes", context.nodes), ("edges", context.edges)):
            for index, record in enumerate(records):
                properties = record.get("properties")
                if not isinstance(properties, Mapping):
                    continue
                for name in self.PROPERTY_NAMES:
                    if name not in properties:
                        continue
                    value = properties[name]
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                        issues.append(_issue(
                            self,
                            "consistency.confidence_out_of_range",
                            IssueSeverity.ERROR,
                            f"/{kind}/{index}/properties/{name}",
                            "La confidence deve essere numerica e compresa tra 0 e 1.",
                            {"property": name, "record_id": record.get("id")},
                            "Correggere la confidence da evidenze verificabili.",
                        ))
        return tuple(issues)


class AnalysisTimestampRule:
    rule_id = "core.consistency.analysis_timestamp"
    version = "1.0.0"

    def evaluate(self, context: ConsistencyContext) -> tuple[GraphIssue, ...]:
        issues = []
        for index, node in enumerate(context.nodes):
            if node.get("type") != "analysis_run":
                continue
            properties = node.get("properties")
            value = properties.get("created_at") if isinstance(properties, Mapping) else None
            if value is None:
                continue
            try:
                datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                issues.append(_issue(
                    self,
                    "consistency.analysis_timestamp_invalid",
                    IssueSeverity.ERROR,
                    f"/nodes/{index}/properties/created_at",
                    "created_at della run non è un timestamp ISO-8601 valido.",
                    {"record_id": node.get("id")},
                    "Usare un timestamp ISO-8601 derivato dalla run originale.",
                ))
        return tuple(issues)


class RootCauseEvidenceRule:
    rule_id = "core.consistency.root_cause_evidence"
    version = "1.0.0"

    def evaluate(self, context: ConsistencyContext) -> tuple[GraphIssue, ...]:
        explained = {
            str(edge.get("source"))
            for edge in context.edges
            if edge.get("relationship") == "EXPLAINS_ANOMALY"
        }
        issues = []
        for index, node in enumerate(context.nodes):
            if node.get("type") != "root_cause" or str(node.get("id")) in explained:
                continue
            properties = node.get("properties")
            related = properties.get("related_anomalies") if isinstance(properties, Mapping) else None
            if related:
                continue
            issues.append(_issue(
                self,
                "consistency.root_cause_without_anomaly_evidence",
                IssueSeverity.WARNING,
                f"/nodes/{index}",
                "La root cause non è collegata ad alcuna evidenza di anomalia.",
                {"record_id": node.get("id")},
                "Collegare un'anomalia verificata o mantenere la root cause fuori dalle raccomandazioni.",
            ))
        return tuple(issues)


CORE_CONSISTENCY_RULES = (
    AnalysisTimestampRule(),
    ConfidenceRangeRule(),
    RootCauseEvidenceRule(),
)
