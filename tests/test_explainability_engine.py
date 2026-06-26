import json

from services.explainability_engine import ExplainabilityEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine


def _processed_data():
    return {
        "deterministic_summary": {
            "status": "computed",
            "row_count": 4,
            "column_count": 3,
            "columns": ["duration", "status", "created_at"],
            "numeric_columns": ["duration"],
            "categorical_columns": ["status"],
            "datetime_columns": ["created_at"],
            "numeric_summary": {
                "duration": {
                    "count": 4,
                    "mean": 2.5,
                    "median": 2.5,
                    "min": 1,
                    "max": 4,
                    "std": 1.291,
                }
            },
        },
        "analysis_plan": {
            "analysis_type": "time_trend",
            "time_column": "created_at",
            "value_column": "duration",
        },
        "deterministic_results": {
            "analysis_type": "time_trend",
            "time_column": "created_at",
            "points": [
                {"period": "2026-01-01", "value": 1},
                {"period": "2026-02-01", "value": 4},
            ],
        },
        "execution_summary": {"status": "completed", "source": "analysis_engine"},
        "detected_patterns": [
            {
                "pattern_id": "time_performance_analysis",
                "name": "Analisi performance temporali",
                "confidence_score": 0.82,
                "matched_keywords": ["tempo", "sla"],
            }
        ],
        "knowledge_analysis_steps": [
            {
                "analysis_type": "threshold_comparison",
                "pattern_id": "time_performance_analysis",
            }
        ],
        "learning_state": {
            "average_confidence": 0.74,
            "patterns": [
                {
                    "pattern_id": "time_performance_analysis",
                    "confidence_score": 0.74,
                    "status": "active",
                }
            ],
        },
        "analytical_strategy": {
            "strategy_id": "strategy-test",
            "confidence_score": 0.77,
            "recommended_sequence": [
                {
                    "analysis_type": "percentile_analysis",
                    "priority": 1,
                    "required_columns": ["duration"],
                    "rationale": "Usare percentili per leggere la coda.",
                }
            ],
            "excluded_analyses": [],
            "clarification_questions": [],
        },
        "advanced_statistical_results": {
            "status": "computed",
            "numeric_analysis": {
                "duration": {
                    "status": "computed",
                    "percentiles": {"p50": 2.5, "p90": 3.7},
                    "dispersion": {"iqr": 1.5},
                    "outliers": {"iqr": {"outlier_count": 0}},
                }
            },
            "correlation_matrices": {},
            "threshold_comparisons": {
                "duration <= 2": {
                    "status": "computed",
                    "breach_rate": 50.0,
                }
            },
        },
        "anomaly_detection_results": {
            "status": "computed",
            "anomaly_count": 1,
            "anomalies": [
                {
                    "anomaly_type": "sla_violation",
                    "severity": "high",
                    "confidence_score": 0.88,
                    "affected_column": "duration",
                    "evidence": {"breach_count": 2, "breach_rate": 50.0},
                    "recommendation": "Verificare le attivazioni oltre soglia.",
                }
            ],
        },
    }


def _analysis():
    return {
        "user_request": "Analizza SLA e tempi",
        "executive_summary": "I tempi mostrano una quota rilevante oltre soglia.",
        "key_findings": ["P90 elevato rispetto alla mediana."],
        "kpi_summary": [{"name": "Durata media", "value": 2.5}],
        "trend_analysis": [{"summary": "Il trend e crescente."}],
        "anomaly_analysis": [
            {
                "type": "sla_violation",
                "severity": "alta",
                "summary": "Il 50% dei record supera la soglia.",
            }
        ],
        "operational_recommendations": [
            "Separare casi oltre soglia per canale operativo."
        ],
    }


def test_explainability_engine_outputs_required_sections():
    explanation = ExplainabilityEngine().explain_analysis(
        _processed_data(),
        _analysis(),
        user_request="Analizza SLA e tempi",
    )

    required_keys = {
        "reasoning_path",
        "analytical_strategy",
        "engines_used",
        "patterns_applied",
        "statistics_used",
        "anomalies_detected",
        "confidence_score",
        "evidence",
        "conclusions",
        "recommendations",
    }
    assert required_keys.issubset(explanation)
    assert explanation["confidence_score"] > 0
    assert explanation["reasoning_path"]
    assert explanation["evidence"]


def test_explainability_engine_reports_integrated_engines():
    explanation = ExplainabilityEngine().explain_analysis(_processed_data(), _analysis())
    engine_names = {item["name"] for item in explanation["engines_used"]}

    assert "AnalyticalReasoningLayer" in engine_names
    assert "AdvancedStatisticalEngine" in engine_names
    assert "AnomalyDetectionEngine" in engine_names
    assert "LearningEngine" in engine_names
    assert "PatternKnowledgeEngine" in engine_names
    assert "SeniorDataAnalystEngine" in engine_names


def test_explainability_output_is_json_serializable():
    explanation = ExplainabilityEngine().explain_analysis(_processed_data(), _analysis())

    json.dumps(explanation)


def test_report_formatter_contains_required_subsections():
    explanation = ExplainabilityEngine().explain_analysis(_processed_data(), _analysis())
    markdown = ExplainabilityEngine().format_for_report(explanation)

    assert "### Decision Flow" in markdown
    assert "### Evidence" in markdown
    assert "### Confidence" in markdown
    assert "### Algorithms Used" in markdown
    assert "### Pattern Used" in markdown
    assert "### Recommendation Reasoning" in markdown


def test_senior_data_analyst_report_includes_why_this_conclusion():
    analysis = SeniorDataAnalystEngine().analyze(
        _processed_data(),
        user_request="Analizza SLA e tempi",
    )

    assert analysis["explainability"]["confidence_score"] > 0
    assert "## Why this conclusion?" in analysis["final_report"]
    assert "### Decision Flow" in analysis["final_report"]
    assert "### Recommendation Reasoning" in analysis["final_report"]
