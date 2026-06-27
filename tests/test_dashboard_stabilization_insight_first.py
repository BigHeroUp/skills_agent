import pandas as pd

from services.business_insight_generator import BusinessInsightGenerator
from ui.callbacks import build_followup_request_id, should_disable_polling, should_process_followup_request
from ui.layout import create_layout
from utils.chart_generator import ChartGenerator


def _dashboard_df():
    return pd.DataFrame({
        "IDCONTRATTOTLM": [f"C{i:04d}" for i in range(100)],
        "PYID": [f"PY-{i:04d}" for i in range(100)],
        "SMARTMOVE": [True] * 97 + [False] * 3,
        "Categoria": ["A", "B", "C", "A", "B"] * 20,
        "processing_time": list(range(20, 120)),
        "created_at": pd.date_range("2026-01-01", periods=100, freq="D"),
    })


def _titles(charts):
    return [chart.layout.title.text for chart in charts if chart.layout.title.text]


def _find_component_order(component, target_ids):
    found = []

    def visit(node):
        node_id = getattr(node, "id", None)
        if node_id in target_ids:
            found.append(node_id)
        children = getattr(node, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                visit(child)
        elif children is not None and not isinstance(children, str):
            visit(children)

    visit(component)
    return found


def test_identifier_columns_do_not_generate_histogram_boxplot_or_top10():
    payload = ChartGenerator.generate_dashboard_charts(_dashboard_df(), insights={})
    titles = _titles(payload["charts"])

    assert all("IDCONTRATTOTLM" not in title for title in titles)
    assert all("PYID" not in title for title in titles)
    skipped = {item["column"]: item for item in payload["skipped_charts"]}
    assert skipped["IDCONTRATTOTLM"]["semantic_type"] == "IDENTIFIER"
    assert skipped["PYID"]["semantic_type"] == "IDENTIFIER"


def test_quasi_constant_boolean_is_skipped_with_metadata():
    payload = ChartGenerator.generate_dashboard_charts(_dashboard_df(), insights={})
    skipped = {item["column"]: item for item in payload["skipped_charts"]}

    assert "SMARTMOVE" in skipped
    assert skipped["SMARTMOVE"]["semantic_type"] == "BOOLEAN"
    assert skipped["SMARTMOVE"]["reason"] in {"quasi_constant", "boolean_quasi_constant"}
    assert skipped["SMARTMOVE"]["dominant_ratio"] == 0.97


def test_informative_category_and_metric_generate_charts():
    payload = ChartGenerator.generate_dashboard_charts(_dashboard_df(), insights={})
    titles = _titles(payload["charts"])

    assert any("Distribuzione Categoria" in title for title in titles)
    assert any("Distribuzione processing_time" in title for title in titles)
    assert any("Analisi Anomalie" in title for title in titles)


def test_business_insights_explain_skipped_columns():
    payload = ChartGenerator.generate_dashboard_charts(_dashboard_df(), insights={})
    insights = BusinessInsightGenerator().generate_chart_exclusion_insights(
        payload["skipped_charts"]
    )

    assert any("SMARTMOVE è quasi costante" in item for item in insights)
    assert any("IDCONTRATTOTLM è stato riconosciuto come identificativo" in item for item in insights)
    assert any("PYID è stato riconosciuto come identificativo" in item for item in insights)


def test_dashboard_layout_is_insight_first_and_interval_starts_disabled():
    layout = create_layout({"status": "idle", "current_agent": "", "progress": 0})
    order = _find_component_order(layout, {"report-container", "results-container"})

    assert order == ["report-container", "results-container"]
    assert should_disable_polling("completed") is True
    assert should_disable_polling("error") is True
    assert should_disable_polling("processing") is False


def test_followup_request_guard_rejects_duplicate_click():
    request_id = build_followup_request_id(3, " procedi ")

    assert should_process_followup_request(3, "procedi", 2, None) is True
    assert should_process_followup_request(3, " procedi ", 3, request_id) is False
    assert should_process_followup_request(0, "procedi", 0, None) is False
