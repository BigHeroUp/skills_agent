import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.advanced_statistical_engine import AdvancedStatisticalEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def _engine():
    return AdvancedStatisticalEngine()


def test_empty_dataframe_returns_json_safe_empty_status():
    result = _engine().analyze_dataframe(pd.DataFrame())

    assert result["status"] == "empty"
    assert result["row_count"] == 0
    json.dumps(result)


def test_numeric_percentiles_are_computed():
    df = pd.DataFrame({"value": list(range(1, 101))})

    result = _engine().analyze_numeric_column(df, "value")

    assert result["status"] == "computed"
    assert result["percentiles"]["p50"] == 50.5
    assert result["percentiles"]["p90"] == 90.1
    assert "p99" in result["percentiles"]


def test_iqr_dispersion_is_computed():
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})

    result = _engine().analyze_numeric_column(df, "value")

    assert result["dispersion"]["iqr"] == 2.0
    assert result["dispersion"]["range"] == 4.0


def test_zscore_outlier_detection():
    df = pd.DataFrame({"value": [10] * 30 + [100]})

    result = _engine().detect_outliers(df, "value", method="zscore")

    assert result["status"] == "computed"
    assert result["outlier_count"] == 1
    assert result["outlier_values"] == [100.0]


def test_modified_zscore_outlier_detection():
    df = pd.DataFrame({"value": [10, 11, 12, 13, 14, 15, 100]})

    result = _engine().detect_outliers(df, "value", method="modified_zscore")

    assert result["status"] == "computed"
    assert result["outlier_count"] == 1
    assert result["outlier_values"] == [100.0]


def test_trend_rolling_mean():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=4, freq="MS"),
        "value": [10, 20, 30, 40],
    })

    result = _engine().analyze_trend(
        df,
        "date",
        "value",
        {"frequency": "MS", "rolling_window": 2},
    )

    assert result["status"] == "computed"
    assert result["points"][1]["rolling_mean"] == 15.0
    assert result["points"][3]["growth_percent"] == 33.3333


def test_threshold_comparison():
    df = pd.DataFrame({"duration": [1, 2, 3, 4]})

    result = _engine().compare_threshold(df, "duration", 2, operator="<=")

    assert result["status"] == "computed"
    assert result["compliant_count"] == 2
    assert result["breach_count"] == 2
    assert result["breach_rate"] == 50.0


def test_correlation_matrix():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4],
        "b": [2, 4, 6, 8],
        "label": ["x", "y", "z", "w"],
    })

    result = _engine().build_correlation_matrix(df, method="pearson")

    assert result["status"] == "computed"
    assert result["matrix"]["a"]["b"] == 1.0
    assert result["top_pairs"][0]["columns"] == ["a", "b"]


def test_kendall_optional_dependency_failure_does_not_block_other_correlations(monkeypatch):
    df = pd.DataFrame({
        "a": [1, 2, 3, 4],
        "b": [2, 4, 6, 8],
    })
    original_corr = pd.DataFrame.corr

    def fake_corr(self, method="pearson", *args, **kwargs):
        if method == "kendall":
            raise ImportError("Missing optional dependency 'scipy'")
        return original_corr(self, method=method, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "corr", fake_corr)

    result = _engine().analyze_dataframe(
        df,
        config={"correlation_methods": ["pearson", "spearman", "kendall"]},
    )

    assert result["correlation_matrices"]["pearson"]["status"] == "computed"
    assert result["correlation_matrices"]["spearman"]["status"] == "computed"
    assert result["correlation_matrices"]["kendall"] == {
        "status": "skipped",
        "reason": "optional_dependency_missing",
        "method": "kendall",
        "error": "Missing optional dependency 'scipy'",
    }
    json.dumps(result)


def test_missing_completeness_analysis():
    df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})

    result = _engine().analyze_dataframe(df)

    completeness = result["missing_completeness"]
    assert completeness["total_missing"] == 2
    assert completeness["columns"]["a"]["missing_count"] == 1
    assert completeness["overall_completeness_percent"] == 66.6667


def test_exported_results_are_json_serializable():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=3, freq="MS"),
        "value": [1, 2, 3],
        "category": ["a", "a", "b"],
    })

    result = _engine().analyze_dataframe(df)
    summary = _engine().export_statistical_summary(result)

    json.dumps(result)
    json.dumps(summary)
    assert summary["numeric_column_count"] == 1


def test_data_processor_stores_advanced_statistical_results(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="Analizza performance SLA e percentili",
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.date_range("2026-01-01", periods=5, freq="D"),
                "duration_hours": [1, 2, 3, 4, 100],
                "status": ["ok", "ok", "late", "ok", "late"],
            })
        },
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.advanced_statistical_results["status"] == "computed"
    assert "duration_hours" in result.advanced_statistical_results["numeric_analysis"]
    assert result.processed_data["advanced_statistical_results"] == (
        result.advanced_statistical_results
    )
