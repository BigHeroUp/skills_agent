import json

import pytest

from services.experience.experience_engine import AnalyticalExperienceEngine
from services.knowledge_graph.consistency import (
    ConsistencyStatus,
    DomainPackConsistencyRules,
    evaluate_consistency,
)
from services.knowledge_graph.domain import GraphIssue, IssueSeverity
from services.knowledge_graph.validation import validate_graph


def _write(tmp_path, payload):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _graph(properties=None):
    return {
        "schema_version": 1,
        "nodes": [{
            "id": "run:1",
            "type": "analysis_run",
            "label": "Run",
            "properties": properties or {"created_at": "2026-01-01T10:00:00"},
        }],
        "edges": [],
    }


def test_core_consistency_accepts_semantically_valid_graph(tmp_path):
    validation = validate_graph(_write(tmp_path, _graph()))

    report = evaluate_consistency(validation)

    assert report.status == ConsistencyStatus.CONSISTENT
    assert report.can_inform_experience is True
    assert report.can_inform_recommendations is True
    assert len(report.evaluated_rule_ids) == 3
    assert json.dumps(report.to_dict(), allow_nan=False)


def test_confidence_and_timestamp_errors_block_downstream_admission(tmp_path):
    validation = validate_graph(_write(tmp_path, _graph({
        "created_at": "not-a-date",
        "confidence": 1.5,
    })))

    report = evaluate_consistency(validation)
    codes = {item.code for item in report.issues}

    assert report.status == ConsistencyStatus.INCONSISTENT
    assert "consistency.confidence_out_of_range" in codes
    assert "consistency.analysis_timestamp_invalid" in codes
    assert report.can_inform_experience is False
    assert report.can_inform_recommendations is False


def test_structurally_inadmissible_graph_is_not_semantically_evaluated(tmp_path):
    validation = validate_graph(_write(tmp_path, {
        "schema_version": 1,
        "nodes": [{"id": "duplicate"}, {"id": "duplicate"}],
        "edges": [],
    }))

    report = evaluate_consistency(validation)

    assert report.status == ConsistencyStatus.NOT_EVALUATED
    assert report.evaluated_rule_ids == ()


def test_domain_pack_rules_are_additive_and_namespaced(tmp_path):
    class RetailRule:
        rule_id = "domain_pack.retail.run_present"
        version = "1.0.0"

        def evaluate(self, context):
            return (GraphIssue(
                code="retail.review_required",
                severity=IssueSeverity.WARNING,
                category="knowledge_consistency",
                location="/",
                message="Retail review required.",
                rule_id=self.rule_id,
                rule_version=self.version,
            ),)

    validation = validate_graph(_write(tmp_path, _graph()))
    extension = DomainPackConsistencyRules("retail", (RetailRule(),))

    report = evaluate_consistency(validation, domain_pack_rules=(extension,))

    assert report.status == ConsistencyStatus.DEGRADED
    assert "domain_pack.retail.run_present" in report.evaluated_rule_ids
    with pytest.raises(ValueError, match="must start"):
        DomainPackConsistencyRules("retail", (type(
            "BadRule",
            (),
            {"rule_id": "core.bad", "version": "1", "evaluate": lambda self, context: ()},
        )(),))


def test_experience_and_recommendations_honor_consistency_gate(tmp_path):
    validation = validate_graph(_write(tmp_path, _graph({"confidence": 2})))
    report = evaluate_consistency(validation)
    engine = AnalyticalExperienceEngine(
        experience_path=tmp_path / "experience.json",
        kg_path=tmp_path / "missing.json",
    )

    refresh = engine.refresh_experience_from_kg(consistency_report=report)
    recommendations = engine.recommend_from_experience({}, consistency_report=report)

    assert refresh["status"] == "blocked_by_consistency"
    assert recommendations["status"] == "blocked_by_consistency"
    assert recommendations["recommendations"] == []
