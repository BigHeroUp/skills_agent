import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.explainability_engine import ExplainabilityEngine
from services.root_cause_analysis_engine import RootCauseAnalysisEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def _payload():
    return {
        "user_request": "Spiega perché crescono anomalie e SLA duration",
        "anomaly_detection_results": {
            "status": "computed",
            "anomaly_count": 3,
            "anomalies": [
                {
                    "anomaly_id": "a1",
                    "anomaly_type": "sla_violation",
                    "severity": "high",
                    "confidence_score": 0.82,
                    "affected_column": "duration",
                    "affected_period": "2026-01",
                    "observed_value": 42,
                    "expected_value": 24,
                    "deviation": 18,
                    "method": "threshold_comparison",
                    "evidence": {"breach_count": 12, "breach_rate": 30.0},
                    "recommendation": "Verificare soglia SLA e backlog operativo.",
                },
                {
                    "anomaly_id": "a2",
                    "anomaly_type": "performance_degradation",
                    "severity": "high",
                    "confidence_score": 0.86,
                    "affected_column": "duration",
                    "affected_period": "2026-01",
                    "observed_value": 48,
                    "expected_value": 28,
                    "deviation": 20,
                    "method": "degradation_detection",
                    "evidence": {"baseline_mean": 28, "recent_mean": 48},
                },
                {
                    "anomaly_id": "a3",
                    "anomaly_type": "time_series_spike",
                    "severity": "medium",
                    "confidence_score": 0.74,
                    "affected_column": "volume",
                    "affected_period": "2026-01",
                    "observed_value": 1200,
                    "expected_value": 700,
                    "deviation": 500,
                    "method": "rolling_baseline",
                    "evidence": {"period": "2026-01"},
                },
            ],
        },
        "advanced_statistical_results": {
            "status": "computed",
            "numeric_analysis": {
                "duration": {
                    "status": "computed",
                    "percentiles": {"p50": 22, "p90": 45, "p95": 52},
                    "dispersion": {"iqr": 18},
                    "outliers": {"iqr": {"outlier_count": 4}},
                }
            },
            "threshold_comparisons": {
                "duration<=24": {
                    "status": "computed",
                    "breach_rate": 30.0,
                    "breach_count": 12,
                }
            },
        },
        "analytical_strategy": {
            "recommended_sequence": [
                {
                    "analysis_type": "root_cause_analysis",
                    "rationale": "La richiesta chiede cause radice.",
                    "confidence_score": 0.8,
                }
            ]
        },
        "detected_patterns": [
            {
                "pattern_id": "time_performance_analysis",
                "confidence_score": 0.9,
                "matched_keywords": ["sla", "duration"],
            }
        ],
        "domain_pack_context": {
            "status": "detected",
            "pack_id": "telepedaggio",
            "suggestion": {"name": "Telepedaggio"},
        },
    }


def test_no_anomalies_returns_insufficient_evidence():
    result = RootCauseAnalysisEngine().analyze({
        "anomaly_detection_results": {"status": "computed", "anomaly_count": 0, "anomalies": []}
    })

    assert result["status"] == "insufficient_evidence"
    assert result["possible_causes"] == []


def test_groups_anomalies_by_same_column():
    anomalies = _payload()["anomaly_detection_results"]["anomalies"][:2]

    groups = RootCauseAnalysisEngine().group_related_anomalies(anomalies)

    assert len(groups) == 1
    assert groups[0]["affected_metrics"] == ["duration"]
    assert "same_column" in groups[0]["relationship_reasons"]


def test_groups_anomalies_by_similar_period():
    anomalies = [
        _payload()["anomaly_detection_results"]["anomalies"][0],
        _payload()["anomaly_detection_results"]["anomalies"][2],
    ]

    groups = RootCauseAnalysisEngine().group_related_anomalies(anomalies)

    assert len(groups) == 1
    assert "same_or_similar_period" in groups[0]["relationship_reasons"]
    assert set(groups[0]["affected_metrics"]) == {"duration", "volume"}


def test_infers_cause_with_multiple_evidences():
    result = RootCauseAnalysisEngine().analyze(_payload())

    assert result["status"] == "computed"
    cause = result["possible_causes"][0]
    assert cause["cause_id"]
    assert cause["severity"] == "high"
    assert cause["confidence_score"] > 0
    assert len(cause["supporting_evidence"]) > 1
    assert cause["alternative_explanations"]
    assert cause["recommended_actions"]
    assert cause["reasoning_trace"]["domain_guidance"] == "Telepedaggio"


def test_ranks_causes_by_severity_and_confidence():
    causes = [
        {"cause_id": "low", "severity": "low", "confidence_score": 0.99, "supporting_evidence": []},
        {"cause_id": "critical", "severity": "critical", "confidence_score": 0.5, "supporting_evidence": []},
        {"cause_id": "high", "severity": "high", "confidence_score": 0.95, "supporting_evidence": []},
    ]

    ranked = RootCauseAnalysisEngine().rank_causes(causes)

    assert [item["cause_id"] for item in ranked] == ["critical", "high", "low"]


def test_root_cause_output_is_json_serializable():
    result = RootCauseAnalysisEngine().analyze(_payload())
    summary = RootCauseAnalysisEngine().export_root_cause_summary(result)

    json.dumps(result)
    json.dumps(summary)
    assert summary["root_cause_count"] == result["root_cause_count"]


def test_senior_report_includes_root_cause_section():
    root_cause_results = RootCauseAnalysisEngine().analyze(_payload())
    processed_data = {
        "deterministic_summary": {
            "row_count": 3,
            "column_count": 2,
            "columns": ["duration", "volume"],
            "numeric_columns": ["duration", "volume"],
            "categorical_columns": [],
            "datetime_columns": [],
        },
        "deterministic_results": {},
        "root_cause_results": root_cause_results,
    }

    analysis = SeniorDataAnalystEngine().analyze(processed_data, "Spiega cause anomalie")

    assert "## Possibili cause radice" in analysis["final_report"]
    assert root_cause_results["possible_causes"][0]["title"] in analysis["final_report"]


def test_explainability_engine_includes_root_cause_in_reasoning_and_evidence():
    root_cause_results = RootCauseAnalysisEngine().analyze(_payload())
    explanation = ExplainabilityEngine().explain_analysis({
        "analytical_strategy": _payload()["analytical_strategy"],
        "anomaly_detection_results": _payload()["anomaly_detection_results"],
        "advanced_statistical_results": _payload()["advanced_statistical_results"],
        "detected_patterns": _payload()["detected_patterns"],
        "root_cause_results": root_cause_results,
    })

    assert any(step["step"] == "root_cause_analysis" for step in explanation["reasoning_path"])
    assert any(item["source"] == "root_cause_analysis_engine" for item in explanation["evidence"])


def test_data_processor_stores_root_cause_results(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="Spiega root cause e motivo delle anomalie duration SLA",
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.date_range("2026-01-01", periods=8, freq="MS"),
                "duration_hours": [10, 10, 10, 11, 12, 60, 70, 120],
                "status": ["ok"] * 8,
            })
        },
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.root_cause_results["status"] in {"computed", "insufficient_evidence"}
    assert "root_cause_results" in result.processed_data
    assert result.processed_data["root_cause_results"] == result.root_cause_results
