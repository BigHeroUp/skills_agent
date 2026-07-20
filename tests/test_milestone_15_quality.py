import pandas as pd

from agents.query_suggestion_agent import QuerySuggestionAgent
from services.anomaly_detection_engine import AnomalyDetectionEngine
from ui.callbacks import build_product_intelligence_cards
from utils.context import AgentContext
from coordinator import Coordinator


def test_csv_query_suggestion_accepts_pandas_columns(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    context = AgentContext(
        user_input="Analizza ricavi per regione",
        raw_data={"dataframe": pd.DataFrame({"region": ["N"], "revenue": [100]})},
        metadata={"source_type": "csv"},
    )

    result = QuerySuggestionAgent().process(context)

    assert result.errors == []
    assert result.raw_data["extraction_suggestion"]["value_column"] == "revenue"


def test_same_numeric_outlier_is_one_anomaly_with_multiple_methods():
    frame = pd.DataFrame({"revenue": [100, 101, 99, 102, 100, 1000]})
    engine = AnomalyDetectionEngine()

    result = engine.detect_anomalies(frame)

    assert result["anomaly_count"] == 1
    assert result["anomalies"][0]["detection_count"] >= 2
    assert "iqr" in result["anomalies"][0]["detection_methods"]


def test_product_intelligence_cards_expose_selected_action():
    context = AgentContext(product_intelligence={
        "status": "completed",
        "consistency": {"status": "consistent"},
        "recommendation": {"recommendations": [{}, {}]},
        "decision": {"status": "selected", "selected": {
            "action": "Validate revenue anomaly", "evidence_score": 0.8, "risk": "low"
        }},
        "observability": {"total_duration_ms": 12.5},
    })

    cards = build_product_intelligence_cards(context)

    assert len(cards) == 6
    assert "Validate revenue anomaly" in str(cards[-1])


def test_csv_coordinator_demo_completes_without_query_suggestion_error(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    frame = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=8, freq="MS"),
        "region": ["North", "South"] * 4,
        "revenue": [100, 102, 104, 103, 105, 101, 107, 30],
        "orders": [10, 11, 10, 12, 11, 10, 12, 2],
    })

    result = Coordinator().run(
        "Analizza ricavi e ordini per regione e individua anomalie",
        metadata={"source_type": "csv", "dataframe": frame, "file_path": "demo.csv"},
    )

    assert not any("truth value of a Index" in error for error in result.errors)
    assert result.final_report
    assert result.product_intelligence.get("status") in {"completed", "completed_without_decision"}
