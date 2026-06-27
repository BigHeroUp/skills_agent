"""Insight business locali per dashboard e report."""

from __future__ import annotations

from typing import Any

import pandas as pd


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

    def generate_activation_time_insights(
        self,
        df: pd.DataFrame,
        feature_results: dict[str, Any] | None = None,
    ) -> list[str]:
        metric = "TEMPO_ATTIVAZIONE_GIORNI"
        if not isinstance(df, pd.DataFrame) or metric not in df.columns:
            return []
        values = pd.to_numeric(df[metric], errors="coerce").dropna()
        if values.empty:
            return []
        insights = [
            f"La mediana dei tempi di attivazione è {values.median():.1f} giorni.",
            f"Il P95 è {values.quantile(0.95):.1f} giorni: il 5% dei casi supera questa durata.",
        ]
        if values.quantile(0.95) >= max(values.median() * 2, values.median() + 1):
            insights.append("La distribuzione presenta una coda lunga: pochi casi estremi allungano sensibilmente i tempi.")
        else:
            insights.append("La distribuzione non mostra una coda lunga estrema rispetto alla mediana.")

        method_col = self._find_method_column(df)
        if method_col:
            grouped = df.assign(**{metric: pd.to_numeric(df[metric], errors="coerce")}).groupby(method_col)[metric].mean().dropna()
            if not grouped.empty:
                leader = grouped.sort_values(ascending=False).index[0]
                insights.append(
                    f"Il metodo di consegna {leader} presenta tempi medi superiori rispetto agli altri."
                )
        insights.append("Sono stati esclusi ID e codici tecnici dalle statistiche descrittive.")
        return insights

    def _find_method_column(self, df: pd.DataFrame):
        for column in df.columns:
            normalized = str(column).lower().replace("_", "")
            if "metodoconsegna" in normalized:
                return column
        return None
