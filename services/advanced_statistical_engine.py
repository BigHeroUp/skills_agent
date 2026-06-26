"""Motore statistico avanzato locale basato su pandas/numpy."""

from __future__ import annotations

import json
import math
import operator as operator_module
from typing import Any

import numpy as np
import pandas as pd


class AdvancedStatisticalEngine:
    """Esegue analisi statistiche avanzate senza chiamate esterne."""

    SCHEMA_VERSION = 1
    PERCENTILES = (10, 25, 50, 75, 90, 95, 99)

    def analyze_dataframe(self, df, config: dict | None = None) -> dict:
        """Analizza dataframe completo con statistiche, qualita e correlazioni."""
        cfg = config if isinstance(config, dict) else {}
        if not isinstance(df, pd.DataFrame) or df.empty:
            return self._json_safe({
                "schema_version": self.SCHEMA_VERSION,
                "status": "empty",
                "row_count": 0,
                "column_count": 0,
                "numeric_columns": [],
                "categorical_columns": [],
                "datetime_columns": [],
                "numeric_analysis": {},
                "correlation_matrices": {},
                "frequency_tables": {},
                "missing_completeness": self._missing_completeness(df),
            })

        numeric_columns = [str(column) for column in df.select_dtypes(include="number").columns]
        categorical_columns = [
            str(column)
            for column in df.columns
            if (
                pd.api.types.is_object_dtype(df[column])
                or pd.api.types.is_string_dtype(df[column])
                or isinstance(df[column].dtype, pd.CategoricalDtype)
                or pd.api.types.is_bool_dtype(df[column])
            )
        ]
        datetime_columns = self._datetime_columns(df)
        numeric_analysis = {
            column: self.analyze_numeric_column(df, column, cfg)
            for column in numeric_columns
        }
        correlations = {}
        for method in cfg.get("correlation_methods", ["pearson", "spearman", "kendall"]):
            result = self.build_correlation_matrix(df, method=method)
            correlations[method] = result
        frequency_tables = {
            column: self._frequency_table(df, column, int(cfg.get("top_n", 10)))
            for column in categorical_columns[: int(cfg.get("max_frequency_columns", 10))]
        }

        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": "computed",
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "datetime_columns": datetime_columns,
            "numeric_analysis": numeric_analysis,
            "correlation_matrices": correlations,
            "frequency_tables": frequency_tables,
            "missing_completeness": self._missing_completeness(df),
        })

    def analyze_numeric_column(
        self,
        df,
        column: str,
        config: dict | None = None,
    ) -> dict:
        """Calcola statistiche robuste per una colonna numerica."""
        cfg = config if isinstance(config, dict) else {}
        if not self._valid_column(df, column):
            return self._status("missing_column", column=column)
        series = self._numeric_series(df[column])
        if series.empty:
            return self._status("non_numeric_or_empty", column=column)

        percentiles = {
            f"p{percentile}": self._round(series.quantile(percentile / 100))
            for percentile in self.PERCENTILES
        }
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        mean = float(series.mean())
        median = float(series.median())
        std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        variance = float(series.var(ddof=1)) if len(series) > 1 else 0.0
        mad = float((series - median).abs().median())
        minimum = float(series.min())
        maximum = float(series.max())
        outlier_methods = cfg.get("outlier_methods", ["iqr", "zscore", "modified_zscore"])
        outliers = {
            method: self.detect_outliers(df, column, method=method)
            for method in outlier_methods
        }

        return self._json_safe({
            "status": "computed",
            "column": str(column),
            "count": int(series.count()),
            "missing_count": int(df[column].isna().sum()),
            "descriptive_statistics": {
                "mean": self._round(mean),
                "median": self._round(median),
                "min": self._round(minimum),
                "max": self._round(maximum),
                "sum": self._round(series.sum()),
            },
            "percentiles": percentiles,
            "dispersion": {
                "range": self._round(maximum - minimum),
                "iqr": self._round(q3 - q1),
                "variance": self._round(variance),
                "standard_deviation": self._round(std),
                "coefficient_of_variation": (
                    self._round(std / abs(mean)) if mean != 0 else None
                ),
                "mad": self._round(mad),
            },
            "outliers": outliers,
        })

    def detect_outliers(self, df, column: str, method: str = "iqr") -> dict:
        """Rileva outlier con IQR, z-score o modified z-score."""
        if not self._valid_column(df, column):
            return self._status("missing_column", column=column, method=method)
        series = self._numeric_series(df[column])
        if series.empty:
            return self._status("non_numeric_or_empty", column=column, method=method)

        normalized = str(method or "iqr").lower()
        mask = pd.Series(False, index=series.index)
        details: dict[str, Any] = {}

        if normalized == "iqr":
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (series < lower) | (series > upper)
            details = {"q1": q1, "q3": q3, "iqr": iqr, "lower_bound": lower, "upper_bound": upper}
        elif normalized in {"z", "zscore", "z-score"}:
            mean = float(series.mean())
            std = float(series.std(ddof=0))
            if std > 0:
                scores = (series - mean) / std
                threshold = 3.0
                mask = scores.abs() > threshold
            else:
                scores = pd.Series(0.0, index=series.index)
                threshold = 3.0
            details = {"mean": mean, "standard_deviation": std, "threshold": threshold}
        elif normalized in {"modified_zscore", "modified-zscore", "modified_z_score"}:
            median = float(series.median())
            mad = float((series - median).abs().median())
            threshold = 3.5
            if mad > 0:
                scores = 0.6745 * (series - median) / mad
                mask = scores.abs() > threshold
            else:
                scores = pd.Series(0.0, index=series.index)
            details = {"median": median, "mad": mad, "threshold": threshold}
        else:
            return self._status("unsupported_method", column=column, method=method)

        outlier_values = series[mask]
        return self._json_safe({
            "status": "computed",
            "column": str(column),
            "method": normalized,
            "outlier_count": int(mask.sum()),
            "outlier_percent": self._round(mask.sum() / len(series) * 100),
            "outlier_indices": [self._safe_scalar(index) for index in outlier_values.index.tolist()],
            "outlier_values": [self._round(value) for value in outlier_values.tolist()],
            "details": details,
        })

    def analyze_trend(
        self,
        df,
        time_column: str,
        value_column: str | None = None,
        config: dict | None = None,
    ) -> dict:
        """Calcola trend temporali, rolling mean/std, growth e MoM."""
        cfg = config if isinstance(config, dict) else {}
        if not self._valid_column(df, time_column):
            return self._status("missing_column", column=time_column)
        data = df.copy()
        parsed_time = pd.to_datetime(data[time_column], errors="coerce")
        valid_time = parsed_time.notna()
        if not valid_time.any():
            return self._status("invalid_datetime", column=time_column)
        data = data.loc[valid_time].copy()
        data["_stat_time"] = parsed_time.loc[valid_time]

        if value_column is not None:
            if not self._valid_column(data, value_column):
                return self._status("missing_column", column=value_column)
            values = pd.to_numeric(data[value_column], errors="coerce")
            data = data.loc[values.notna()].copy()
            data["_stat_value"] = values.loc[values.notna()]
            aggregation = str(cfg.get("aggregation", "mean"))
            if data.empty:
                return self._status("non_numeric_or_empty", column=value_column)
        else:
            data["_stat_value"] = 1
            aggregation = "count"

        frequency = str(cfg.get("frequency", "M"))
        window = int(cfg.get("rolling_window", 3))
        grouped = (
            data.set_index("_stat_time")["_stat_value"]
            .resample(frequency)
            .agg(aggregation)
            .dropna()
        )
        if grouped.empty:
            return self._status("empty_trend", column=time_column)
        rolling_mean = grouped.rolling(window=window, min_periods=1).mean()
        rolling_std = grouped.rolling(window=window, min_periods=2).std()
        growth = grouped.pct_change() * 100
        first = float(grouped.iloc[0])
        last = float(grouped.iloc[-1])
        total_growth = None if first == 0 else (last - first) / abs(first) * 100

        points = []
        for timestamp, value in grouped.items():
            points.append({
                "period": timestamp.isoformat(),
                "value": self._round(value),
                "rolling_mean": self._round(rolling_mean.loc[timestamp]),
                "rolling_std": self._round(rolling_std.loc[timestamp]),
                "growth_percent": self._round(growth.loc[timestamp]),
                "month_over_month_percent": self._round(growth.loc[timestamp]),
            })

        return self._json_safe({
            "status": "computed",
            "time_column": str(time_column),
            "value_column": str(value_column) if value_column else None,
            "aggregation": aggregation,
            "frequency": frequency,
            "rolling_window": window,
            "point_count": len(points),
            "first_value": self._round(first),
            "last_value": self._round(last),
            "total_growth_percent": self._round(total_growth),
            "points": points,
        })

    def compare_threshold(
        self,
        df,
        column: str,
        threshold: float,
        operator: str = "<=",
    ) -> dict:
        """Confronta una colonna numerica con una soglia."""
        if not self._valid_column(df, column):
            return self._status("missing_column", column=column)
        series = self._numeric_series(df[column])
        if series.empty:
            return self._status("non_numeric_or_empty", column=column)
        try:
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            return self._status("invalid_threshold", column=column)
        operations = {
            "<=": operator_module.le,
            "<": operator_module.lt,
            ">=": operator_module.ge,
            ">": operator_module.gt,
            "==": operator_module.eq,
            "!=": operator_module.ne,
        }
        operation = operations.get(str(operator))
        if operation is None:
            return self._status("unsupported_operator", column=column, operator=operator)
        compliant = operation(series, threshold_value)
        compliant_count = int(compliant.sum())
        breach_count = int(len(series) - compliant_count)
        return self._json_safe({
            "status": "computed",
            "column": str(column),
            "threshold": self._round(threshold_value),
            "operator": str(operator),
            "valid_count": int(len(series)),
            "compliant_count": compliant_count,
            "breach_count": breach_count,
            "compliance_rate": self._round(compliant_count / len(series) * 100),
            "breach_rate": self._round(breach_count / len(series) * 100),
            "breach_indices": [self._safe_scalar(index) for index in series[~compliant].index.tolist()],
        })

    def build_correlation_matrix(self, df, method: str = "pearson") -> dict:
        """Costruisce matrice di correlazione numerica."""
        if not isinstance(df, pd.DataFrame) or df.empty:
            return self._status("empty", method=method)
        numeric = df.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            return self._status("insufficient_numeric_columns", method=method)
        normalized = str(method or "pearson").lower()
        if normalized not in {"pearson", "spearman", "kendall"}:
            return self._status("unsupported_method", method=method)
        matrix = numeric.corr(method=normalized)
        pairs = []
        columns = list(matrix.columns)
        for left_index, left in enumerate(columns):
            for right in columns[left_index + 1:]:
                value = matrix.loc[left, right]
                if pd.notna(value):
                    pairs.append({
                        "columns": [str(left), str(right)],
                        "correlation": self._round(value),
                        "correlation_abs": self._round(abs(float(value))),
                    })
        pairs.sort(key=lambda item: item["correlation_abs"], reverse=True)
        return self._json_safe({
            "status": "computed",
            "method": normalized,
            "columns": [str(column) for column in columns],
            "matrix": {
                str(index): {
                    str(column): self._round(value)
                    for column, value in row.items()
                }
                for index, row in matrix.to_dict(orient="index").items()
            },
            "top_pairs": pairs[:10],
        })

    def export_statistical_summary(self, results: dict) -> dict:
        """Esporta sintesi compatta dei risultati statistici."""
        data = results if isinstance(results, dict) else {}
        numeric = data.get("numeric_analysis") or {}
        outlier_summary = []
        percentile_summary = {}
        for column, analysis in numeric.items():
            if not isinstance(analysis, dict) or analysis.get("status") != "computed":
                continue
            percentile_summary[column] = analysis.get("percentiles", {})
            methods = analysis.get("outliers") or {}
            outlier_summary.append({
                "column": column,
                "iqr_outliers": methods.get("iqr", {}).get("outlier_count", 0),
                "zscore_outliers": methods.get("zscore", {}).get(
                    "outlier_count",
                    methods.get("z-score", {}).get("outlier_count", 0),
                ),
                "modified_zscore_outliers": methods.get("modified_zscore", {}).get("outlier_count", 0),
            })
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": data.get("status", "unknown"),
            "row_count": data.get("row_count", 0),
            "column_count": data.get("column_count", 0),
            "numeric_column_count": len(data.get("numeric_columns") or []),
            "categorical_column_count": len(data.get("categorical_columns") or []),
            "datetime_column_count": len(data.get("datetime_columns") or []),
            "percentiles": percentile_summary,
            "outliers": outlier_summary,
            "missing_completeness": data.get("missing_completeness", {}),
            "correlation_methods": list((data.get("correlation_matrices") or {}).keys()),
        })

    def _missing_completeness(self, df) -> dict:
        if not isinstance(df, pd.DataFrame):
            return {
                "status": "empty",
                "row_count": 0,
                "column_count": 0,
                "columns": {},
                "overall_completeness_percent": 0.0,
            }
        row_count = int(len(df))
        column_count = int(len(df.columns))
        total_cells = row_count * column_count
        columns = {}
        for column in df.columns:
            missing = int(df[column].isna().sum())
            completeness = 0.0 if row_count == 0 else (row_count - missing) / row_count * 100
            columns[str(column)] = {
                "missing_count": missing,
                "missing_percent": self._round(0.0 if row_count == 0 else missing / row_count * 100),
                "complete_count": int(row_count - missing),
                "completeness_percent": self._round(completeness),
            }
        total_missing = int(df.isna().sum().sum()) if total_cells else 0
        return self._json_safe({
            "status": "computed" if total_cells else "empty",
            "row_count": row_count,
            "column_count": column_count,
            "total_cells": total_cells,
            "total_missing": total_missing,
            "overall_completeness_percent": self._round(
                0.0 if total_cells == 0 else (total_cells - total_missing) / total_cells * 100
            ),
            "columns": columns,
        })

    def _frequency_table(self, df: pd.DataFrame, column: str, top_n: int) -> dict:
        if not self._valid_column(df, column):
            return self._status("missing_column", column=column)
        series = df[column].dropna().astype(str)
        total = int(series.count())
        counts = series.value_counts().head(top_n)
        return self._json_safe({
            "status": "computed",
            "column": str(column),
            "unique_count": int(series.nunique()),
            "non_null_count": total,
            "top_values": [
                {
                    "value": str(value),
                    "count": int(count),
                    "share_percent": self._round(0.0 if total == 0 else count / total * 100),
                }
                for value, count in counts.items()
            ],
        })

    def _datetime_columns(self, df: pd.DataFrame) -> list[str]:
        output = [str(column) for column in df.select_dtypes(include=["datetime", "datetimetz"]).columns]
        for column in df.columns:
            if str(column) in output:
                continue
            name = str(column).lower()
            if "date" not in name and "time" not in name:
                continue
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().any():
                output.append(str(column))
        return output

    def _valid_column(self, df, column: str) -> bool:
        return isinstance(df, pd.DataFrame) and column in df.columns

    def _numeric_series(self, series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce").dropna()

    def _status(self, status: str, **extra: Any) -> dict:
        return self._json_safe({"status": status, **extra})

    def _round(self, value: Any, digits: int = 4) -> Any:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return self._safe_scalar(value)
        if not math.isfinite(number):
            return None
        return round(number, digits)

    def _safe_scalar(self, value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return self._round(float(value))
        if isinstance(value, (pd.Timestamp,)):
            return value.isoformat()
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return self._safe_scalar(value.item())
        return value

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return self._round(float(value))
        if isinstance(value, (pd.Timestamp,)):
            return value.isoformat()
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        json.dumps(value, ensure_ascii=False, default=str)
        return value
