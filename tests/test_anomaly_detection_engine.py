import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.analysis_session_manager import AnalysisSessionManager
from services.advanced_statistical_engine import AdvancedStatisticalEngine
from services.anomaly_detection_engine import AnomalyDetectionEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def _engine():
    return AnomalyDetectionEngine()


def _anomaly_types(result):
    return {item["anomaly_type"] for item in result.get("anomalies", [])}


def test_empty_dataframe_does_not_fail():
    result = _engine().detect_anomalies(pd.DataFrame())

    assert result["status"] == "empty"
    assert result["anomaly_count"] == 0
    assert "Dataframe vuoto" in result["reason"]
    json.dumps(result)


def test_numeric_outlier_detection():
    df = pd.DataFrame({"duration": [10] * 30 + [100]})

    result = _engine().detect_numeric_anomalies(df)

    assert result["status"] == "computed"
    assert "numeric_outlier" in _anomaly_types(result)
    assert any(item["observed_value"] == 100.0 for item in result["anomalies"])


def test_time_series_spike_detection():
    df = pd.DataFrame({
        "period": pd.date_range("2026-01-01", periods=4, freq="MS"),
        "duration": [10, 10, 10, 100],
    })

    result = _engine().detect_time_series_anomalies(
        df,
        "period",
        "duration",
        {"frequency": "MS", "rolling_window": 3, "spike_std_multiplier": 1.0},
    )

    assert result["status"] == "computed"
    assert "time_series_spike" in _anomaly_types(result)


def test_performance_degradation_detection():
    df = pd.DataFrame({
        "period": pd.date_range("2026-01-01", periods=8, freq="MS"),
        "latency": [10, 10, 11, 10, 11, 10, 20, 22],
    })

    result = _engine().detect_degradation(
        df,
        "period",
        "latency",
        {"degradation_window": 2, "degradation_threshold_percent": 20},
    )

    assert result["status"] == "computed"
    assert "performance_degradation" in _anomaly_types(result)
    assert result["anomalies"][0]["severity"] in {"high", "critical"}


def test_compare_against_baseline_detects_drift():
    stats = AdvancedStatisticalEngine()
    baseline = stats.analyze_dataframe(pd.DataFrame({"duration": [10, 11, 9, 10]}))
    current = stats.analyze_dataframe(pd.DataFrame({"duration": [20, 21, 19, 20]}))

    result = _engine().compare_against_baseline(
        current,
        baseline,
        {"drift_threshold_percent": 20},
    )

    assert result["status"] == "computed"
    assert "baseline_drift" in _anomaly_types(result)


def test_sla_violation_detection():
    df = pd.DataFrame({"duration": [1, 2, 3, 4]})

    result = _engine().detect_sla_violations(df, "duration", 2, operator="<=")

    assert result["status"] == "computed"
    assert "sla_violation" in _anomaly_types(result)
    assert result["anomalies"][0]["evidence"]["breach_count"] == 2


def test_severity_is_assigned():
    df = pd.DataFrame({"duration": [1, 2, 3, 4]})

    result = _engine().detect_sla_violations(df, "duration", 2, operator="<=")

    severity = result["anomalies"][0]["severity"]
    assert severity in {"low", "medium", "high", "critical"}
    assert result["anomalies"][0]["confidence_score"] > 0


def test_anomaly_results_are_json_serializable():
    df = pd.DataFrame({
        "period": pd.date_range("2026-01-01", periods=4, freq="MS"),
        "duration": [10, 10, 10, 100],
    })

    result = _engine().detect_anomalies(
        df,
        {
            "time_column": "period",
            "value_column": "duration",
            "frequency": "MS",
            "spike_std_multiplier": 1.0,
        },
    )
    summary = _engine().export_anomaly_summary(result)

    json.dumps(result)
    json.dumps(summary)
    assert summary["anomaly_count"] == result["anomaly_count"]


def test_data_processor_stores_anomaly_detection_results(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="Analizza anomalie outlier e degrado SLA",
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.date_range("2026-01-01", periods=8, freq="MS"),
                "duration_hours": [10, 10, 10, 10, 11, 10, 20, 100],
                "status": ["ok"] * 8,
            })
        },
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.anomaly_detection_results["status"] == "computed"
    assert result.anomaly_detection_results["anomaly_count"] > 0
    assert result.processed_data["anomaly_detection_results"] == (
        result.anomaly_detection_results
    )


def test_analysis_session_manager_stores_anomaly_results():
    manager = AnalysisSessionManager(id_factory=lambda: "session-anomaly")
    session = manager.start_session(
        "Analizza anomalie",
        "csv",
        {"columns": ["duration"], "numeric_columns": ["duration"]},
    )
    payload = {
        "analysis_plan": {},
        "deterministic_results": {},
        "anomaly_detection_results": {
            "status": "computed",
            "anomaly_count": 1,
            "anomalies": [{"anomaly_id": "a1", "severity": "high"}],
        },
    }

    iteration = manager.add_iteration(
        session["session_id"],
        "Analizza anomalie",
        payload,
    )
    context = manager.build_context_for_next_iteration(session["session_id"])

    assert iteration["anomaly_detection_results"]["anomaly_count"] == 1
    assert context["latest_anomaly_detection_results"]["anomalies"][0]["anomaly_id"] == "a1"


def test_senior_data_analyst_report_includes_detected_anomalies_section():
    anomaly_results = _engine().detect_sla_violations(
        pd.DataFrame({"duration": [1, 2, 3, 4]}),
        "duration",
        2,
        operator="<=",
    )
    processed_data = {
        "deterministic_summary": {
            "status": "computed",
            "row_count": 4,
            "column_count": 1,
            "columns": ["duration"],
            "numeric_columns": ["duration"],
            "categorical_columns": [],
            "datetime_columns": [],
        },
        "deterministic_results": {},
        "anomaly_detection_results": anomaly_results,
    }

    analysis = SeniorDataAnalystEngine().analyze(
        processed_data,
        user_request="Analizza violazioni SLA",
    )

    assert "## Anomalie rilevate" in analysis["final_report"]
    assert "sla_violation" in analysis["final_report"]
    assert "Raccomandazione" in analysis["final_report"]
