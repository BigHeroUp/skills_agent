import json

from agents.analyst import AnalystAgent
from agents.report_generator import ReportGeneratorAgent
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.context import AgentContext


def _processed_data():
    return {
        "deterministic_summary": {
            "status": "computed",
            "row_count": 8,
            "column_count": 4,
            "columns": ["stato", "importo", "created_at", "owner"],
            "numeric_columns": ["importo"],
            "categorical_columns": ["stato", "owner"],
            "datetime_columns": ["created_at"],
            "duplicate_rows": 1,
            "missing_values": {
                "owner": {"count": 2, "percent": 25.0},
            },
            "numeric_summary": {
                "importo": {
                    "count": 8,
                    "sum": 1470.0,
                    "mean": 183.75,
                    "median": 105.0,
                    "min": 80.0,
                    "max": 1000.0,
                    "std": 310.0,
                    "missing": 0,
                },
            },
            "categorical_summary": {
                "stato": {
                    "unique": 3,
                    "top_values": {"closed": 5, "open": 2, "pending": 1},
                    "missing": 0,
                },
            },
            "time_ranges": {
                "created_at": {
                    "min": "2026-01-01T00:00:00",
                    "max": "2026-04-01T00:00:00",
                    "valid_values": 8,
                },
            },
        },
        "analysis_plan": {
            "analysis_type": "time_trend",
            "time_column": "created_at",
            "aggregation": "count",
        },
        "deterministic_results": {
            "analysis_type": "time_trend",
            "time_column": "created_at",
            "aggregation": "count",
            "points": [
                {"period": "2026-01-01T00:00:00", "value": 2},
                {"period": "2026-02-01T00:00:00", "value": 3},
                {"period": "2026-03-01T00:00:00", "value": 4},
                {"period": "2026-04-01T00:00:00", "value": 6},
            ],
        },
        "execution_summary": {"status": "completed", "source": "analysis_engine"},
        "autonomous_analysis_results": [
            {
                "step_id": "category-distribution",
                "title": "Distribuzione per stato",
                "status": "completed",
                "result": {
                    "analysis_type": "count_occurrences",
                    "target_column": "stato",
                    "counts": [
                        {"value": "closed", "count": 5},
                        {"value": "open", "count": 2},
                        {"value": "pending", "count": 1},
                    ],
                },
            }
        ],
    }


def test_generates_professional_report_without_openai():
    analysis = SeniorDataAnalystEngine().analyze(
        _processed_data(),
        user_request="Analizza andamento e distribuzione ticket",
    )

    assert analysis["analysis_source"] == "local_deterministic_engine"
    assert analysis["executive_summary"]
    assert analysis["operational_recommendations"]
    assert "# Report business" in analysis["final_report"]
    assert "## Executive Summary" in analysis["final_report"]
    assert "## KPI principali" in analysis["final_report"]
    assert "## Appendice tecnica" in analysis["final_report"]


def test_business_report_avoids_raw_dumps_and_limits_recommendations():
    analysis = SeniorDataAnalystEngine().analyze(
        _processed_data(),
        user_request="Analizza andamento e distribuzione ticket",
    )
    report = analysis["final_report"]
    recommendations = [
        line for line in report.splitlines()
        if line[:2] in {f"{index}." for index in range(1, 10)}
    ]

    assert "local_analysis: {" not in report
    assert "{'" not in report
    assert "'}" not in report
    assert len(recommendations) <= 5
    assert report.count("## Executive Summary") == 1
    assert report.count("## KPI principali") == 1


def test_business_report_filters_uninformative_segments():
    processed_data = _processed_data()
    processed_data["deterministic_summary"]["categorical_summary"] = {
        "SMARTMOVE": {
            "unique": 2,
            "top_values": {"true": 97, "false": 3},
            "missing": 0,
        },
        "PYID": {
            "unique": 8,
            "top_values": {f"PY-{index}": 1 for index in range(8)},
            "missing": 0,
        },
    }
    processed_data["autonomous_analysis_results"] = []

    analysis = SeniorDataAnalystEngine().analyze(processed_data)

    assert "SMARTMOVE" not in analysis["final_report"]
    assert "PYID" not in analysis["final_report"]


def test_handles_time_trend_and_segmentation():
    analysis = SeniorDataAnalystEngine().analyze(_processed_data())

    trend = analysis["trend_analysis"][0]
    assert trend["direction"] == "crescente"
    assert trend["percentage_change"] == 200.0
    assert analysis["segmentation_analysis"][0]["leading_segment"] == "closed"


def test_grouped_numeric_results_preserve_segment_labels():
    processed_data = _processed_data()
    processed_data["deterministic_results"] = {
        "analysis_type": "numeric_aggregation",
        "group_by_column": "stato",
        "value_column": "importo",
        "aggregation": "sum",
        "groups": [
            {"group": "closed", "value": 1200},
            {"group": "open", "value": 270},
        ],
    }

    analysis = SeniorDataAnalystEngine().analyze(processed_data)

    assert analysis["segmentation_analysis"][0]["leading_segment"] == "closed"
    assert analysis["segmentation_analysis"][0]["leading_value"] == 1200


def test_reports_quality_anomalies_and_extreme_values_when_available():
    analysis = SeniorDataAnalystEngine().analyze(_processed_data())
    anomaly_types = {item["type"] for item in analysis["anomaly_analysis"]}

    assert "missing_values" in anomaly_types
    assert "duplicate_rows" in anomaly_types
    assert "potential_extreme_value" in anomaly_types


def test_output_is_json_serializable():
    analysis = SeniorDataAnalystEngine().analyze(_processed_data())

    json.dumps(analysis)


def test_analyst_agent_completes_with_local_engine_without_openai():
    agent = AnalystAgent.__new__(AnalystAgent)
    agent.name = "Analyst"
    agent.local_engine = SeniorDataAnalystEngine()
    agent.client = None
    agent.log = lambda message: None
    context = AgentContext(
        user_input="Analizza i ticket",
        processed_data=_processed_data(),
    )

    result = agent.process(context)

    assert result.insights["analysis_mode"] == "local_only"
    assert result.insights["local_analysis"]["executive_summary"]
    assert result.errors == []


def test_report_generator_uses_local_report_when_openai_is_unavailable():
    local_analysis = SeniorDataAnalystEngine().analyze(_processed_data())
    agent = ReportGeneratorAgent.__new__(ReportGeneratorAgent)
    agent.name = "ReportGenerator"
    agent.local_engine = SeniorDataAnalystEngine()
    agent.client = None
    agent.log = lambda message: None
    context = AgentContext(
        user_input="Analizza i ticket",
        processed_data=_processed_data(),
        insights={"local_analysis": local_analysis},
    )

    result = agent.process(context)

    assert result.final_report == local_analysis["final_report"]
    assert result.errors == []
