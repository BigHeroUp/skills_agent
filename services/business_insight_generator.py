"""Insight business locali per dashboard e report."""

from __future__ import annotations

from typing import Any


class BusinessInsightGenerator:
    """Trasforma metadata tecnici in note leggibili per utenti business."""

    def generate_chart_exclusion_insights(self, skipped_charts: list[dict[str, Any]]) -> list[str]:
        insights = []
        for item in skipped_charts or []:
            column = item.get("column", "colonna")
            semantic_type = item.get("semantic_type", "UNKNOWN")
            reason = item.get("reason", "")
            dominant = item.get("dominant_value")
            dominant_ratio = float(item.get("dominant_ratio", 0) or 0)
            if reason in {"constant", "quasi_constant", "boolean_quasi_constant"}:
                insights.append(
                    f"{column} è quasi costante: valore prevalente {dominant} "
                    f"nel {dominant_ratio * 100:.1f}% dei record. "
                    "Non è stata generata una distribuzione grafica perché poco informativa."
                )
            elif semantic_type == "IDENTIFIER":
                insights.append(
                    f"{column} è stato riconosciuto come identificativo: escluse statistiche numeriche, "
                    "top 10, istogrammi e boxplot."
                )
            elif reason == "technical_code_high_cardinality":
                insights.append(
                    f"{column} è un codice tecnico ad alta cardinalità: escluso dai grafici automatici."
                )
        return list(dict.fromkeys(insights))

    def useful_columns_insight(self, chart_payload: dict[str, Any]) -> str | None:
        charts = chart_payload.get("charts") or []
        useful_columns = []
        for chart in charts:
            title = getattr(getattr(chart, "layout", None), "title", None)
            text = getattr(title, "text", "") or ""
            if text:
                useful_columns.append(text)
        if not useful_columns:
            return None
        return "Le visualizzazioni automatiche sono state limitate alle colonne informative per trend, metriche e distribuzioni business."
