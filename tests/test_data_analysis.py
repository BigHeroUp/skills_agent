import pandas as pd

from utils.data_analysis import build_deterministic_insights, summarize_dataframe


def test_summarize_dataframe_computes_real_metrics():
    df = pd.DataFrame({
        "categoria": ["A", "A", "B", None],
        "vendite": [10, 15, 7, 20],
        "costo": [5, 8, 3, 12],
    })

    summary = summarize_dataframe(df)
    insights = build_deterministic_insights(summary)

    assert summary["status"] == "computed"
    assert summary["row_count"] == 4
    assert summary["column_count"] == 3
    assert summary["numeric_summary"]["vendite"]["sum"] == 52
    assert "categoria" in summary["missing_values"]
    assert insights["key_metrics"]["vendite"]["mean"] == 13
