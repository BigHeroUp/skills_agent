"""
Utility deterministiche per analisi pandas.

Queste funzioni producono risultati calcolati dal dataframe reale, separati dai
testi generati dal modello LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def _safe_value(value: Any) -> Any:
    """Converte valori pandas/numpy in tipi serializzabili e leggibili."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _round(value: Any, digits: int = 4) -> Any:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return _safe_value(value)


def summarize_dataframe(df: pd.DataFrame, top_n: int = 5) -> Dict[str, Any]:
    """Calcola statistiche verificabili dal dataframe reale."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "status": "empty",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
        }

    numeric_cols = list(df.select_dtypes(include="number").columns)
    categorical_cols = [
        column
        for column in df.columns
        if (
            pd.api.types.is_object_dtype(df[column])
            or pd.api.types.is_string_dtype(df[column])
            or isinstance(df[column].dtype, pd.CategoricalDtype)
            or pd.api.types.is_bool_dtype(df[column])
        )
    ]
    datetime_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)

    for column in df.columns:
        name = str(column).lower()
        if column not in datetime_cols and ("date" in name or "time" in name):
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().sum() > 0:
                datetime_cols.append(column)

    missing_counts = df.isna().sum()
    missing_percent = (missing_counts / len(df) * 100).round(2)

    numeric_summary: Dict[str, Dict[str, Any]] = {}
    for column in numeric_cols:
        series = df[column].dropna()
        if series.empty:
            continue
        numeric_summary[str(column)] = {
            "count": int(series.count()),
            "sum": _round(series.sum()),
            "mean": _round(series.mean()),
            "median": _round(series.median()),
            "min": _round(series.min()),
            "max": _round(series.max()),
            "std": _round(series.std()) if len(series) > 1 else 0,
            "missing": int(missing_counts[column]),
        }

    categorical_summary: Dict[str, Dict[str, Any]] = {}
    for column in categorical_cols[:10]:
        counts = df[column].dropna().astype(str).value_counts().head(top_n)
        categorical_summary[str(column)] = {
            "unique": int(df[column].nunique(dropna=True)),
            "top_values": counts.to_dict(),
            "missing": int(missing_counts[column]),
        }

    correlations: List[Dict[str, Any]] = []
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr(numeric_only=True).abs()
        for i, left in enumerate(numeric_cols):
            for right in numeric_cols[i + 1:]:
                value = corr.loc[left, right]
                if pd.notna(value):
                    correlations.append({
                        "columns": [str(left), str(right)],
                        "correlation_abs": _round(value),
                    })
        correlations.sort(key=lambda item: item["correlation_abs"], reverse=True)
        correlations = correlations[:top_n]

    time_ranges: Dict[str, Dict[str, Any]] = {}
    for column in datetime_cols[:5]:
        parsed = pd.to_datetime(df[column], errors="coerce").dropna()
        if parsed.empty:
            continue
        time_ranges[str(column)] = {
            "min": parsed.min().isoformat(),
            "max": parsed.max().isoformat(),
            "valid_values": int(parsed.count()),
        }

    return {
        "status": "computed",
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(column) for column in df.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": {
            str(column): {
                "count": int(missing_counts[column]),
                "percent": _round(missing_percent[column], 2),
            }
            for column in df.columns
            if int(missing_counts[column]) > 0
        },
        "numeric_columns": [str(column) for column in numeric_cols],
        "categorical_columns": [str(column) for column in categorical_cols],
        "datetime_columns": [str(column) for column in datetime_cols],
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "top_correlations": correlations,
        "time_ranges": time_ranges,
    }


def build_deterministic_insights(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Deriva insight semplici e verificabili dal riepilogo deterministico."""
    if summary.get("status") != "computed":
        return {
            "data_quality": ["Nessun dataframe disponibile per calcoli deterministici."],
            "key_metrics": {},
            "warnings": [],
        }

    warnings: List[str] = []
    data_quality: List[str] = []

    row_count = summary.get("row_count", 0)
    column_count = summary.get("column_count", 0)
    data_quality.append(f"Dataset con {row_count} righe e {column_count} colonne.")

    duplicates = summary.get("duplicate_rows", 0)
    if duplicates:
        warnings.append(f"Sono presenti {duplicates} righe duplicate.")

    missing_values = summary.get("missing_values", {})
    if missing_values:
        worst_column, worst_stats = max(
            missing_values.items(),
            key=lambda item: item[1].get("percent", 0),
        )
        warnings.append(
            f"La colonna con piu valori mancanti e {worst_column} "
            f"({worst_stats.get('percent', 0)}%)."
        )
    else:
        data_quality.append("Non risultano valori mancanti.")

    key_metrics: Dict[str, Any] = {}
    for column, stats in list(summary.get("numeric_summary", {}).items())[:5]:
        key_metrics[column] = {
            "sum": stats.get("sum"),
            "mean": stats.get("mean"),
            "min": stats.get("min"),
            "max": stats.get("max"),
        }

    correlations = summary.get("top_correlations", [])
    if correlations:
        best = correlations[0]
        data_quality.append(
            "Correlazione numerica piu alta: "
            f"{best['columns'][0]} / {best['columns'][1]} = {best['correlation_abs']}."
        )

    return {
        "data_quality": data_quality,
        "key_metrics": key_metrics,
        "warnings": warnings,
        "top_correlations": correlations,
        "time_ranges": summary.get("time_ranges", {}),
    }
