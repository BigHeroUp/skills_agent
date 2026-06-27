"""Classificazione semantica locale delle colonne."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


class SemanticColumnClassifier:
    """Classifica colonne usando nome, dtype, cardinalita e parsing date."""

    DATE_NAME_TERMS = {
        "data",
        "date",
        "creazione",
        "agg",
        "update",
        "updated",
        "created",
        "timestamp",
        "sottoscrizione",
        "attivazione",
        "chiusura",
        "apertura",
        "fine",
        "inizio",
    }
    IDENTIFIER_TERMS = {
        "id",
        "pyid",
        "pzinskey",
        "uuid",
        "guid",
        "key",
        "idcontratto",
        "idcontrattotlm",
        "contrattoid",
        "contractid",
        "serialnumber",
        "serial",
        "codicefiscale",
    }
    STATUS_TERMS = {"status", "stato", "state", "esito"}
    DURATION_TERMS = {"tempo", "duration", "durata", "giorni", "attivazione", "sla"}
    AMOUNT_TERMS = {"amount", "importo", "revenue", "costo", "cost", "prezzo"}
    BOOLEAN_VALUES = {"true", "false", "0", "1", "yes", "no", "si", "sì"}

    RULES = {
        "IDENTIFIER": (
            ["uniqueness", "duplicates", "missing_count"],
            ["mean", "median", "std", "boxplot", "histogram", "top10"],
        ),
        "DATE": (
            ["timeline", "trend", "seasonality"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "DATETIME": (
            ["timeline", "trend", "seasonality"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "DURATION": (
            ["distribution", "percentiles", "outliers", "trend"],
            [],
        ),
        "METRIC": (
            ["mean", "median", "percentiles", "distribution", "boxplot", "outliers"],
            [],
        ),
        "AMOUNT": (
            ["sum", "mean", "median", "percentiles", "trend"],
            [],
        ),
        "CATEGORY": (
            ["frequency", "pareto", "bar", "segmentation"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "STATUS": (
            ["frequency", "bar", "transition", "trend"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "BOOLEAN": (
            ["true_false_rate", "frequency"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "CODE": (
            ["cardinality", "frequency", "mapping_quality"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "TEXT": (
            ["completeness", "length_distribution"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
        "UNKNOWN": (
            ["profile", "missing_values"],
            ["mean", "median", "std", "boxplot", "histogram"],
        ),
    }

    def classify_dataframe(self, df: pd.DataFrame, domain_pack_context: dict | None = None) -> dict[str, dict[str, Any]]:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {}
        return {
            str(column): self.classify_column(df, column, domain_pack_context)
            for column in df.columns
        }

    def classify_column(
        self,
        df: pd.DataFrame,
        column,
        domain_pack_context: dict | None = None,
    ) -> dict[str, Any]:
        series = df[column]
        non_null = series.dropna()
        row_count = max(1, len(series))
        distinct_count = int(non_null.nunique(dropna=True))
        unique_ratio = distinct_count / max(1, int(non_null.count()))
        normalized = self._normalize(column)

        semantic_type, confidence, reason = self._infer_type(
            normalized,
            series,
            distinct_count,
            unique_ratio,
            row_count,
        )
        recommended, forbidden = self.RULES.get(semantic_type, self.RULES["UNKNOWN"])
        return {
            "column": str(column),
            "semantic_type": semantic_type,
            "confidence": round(float(confidence), 4),
            "reason": reason,
            "recommended_analysis": list(recommended),
            "forbidden_analysis": list(forbidden),
            "cardinality": distinct_count,
            "unique_ratio": round(unique_ratio, 4),
            "dtype": str(series.dtype),
        }

    def _infer_type(
        self,
        normalized: str,
        series: pd.Series,
        distinct_count: int,
        unique_ratio: float,
        row_count: int,
    ) -> tuple[str, float, str]:
        if any(term in normalized for term in self.DURATION_TERMS):
            return "DURATION", 0.88, "Nome colonna riconducibile a durata o tempo operativo."

        if any(term in normalized for term in self.DATE_NAME_TERMS):
            parsed = self._parse_datetime_candidate(series)
            valid_ratio = float(parsed.notna().mean()) if len(parsed) else 0.0
            if valid_ratio >= 0.3:
                semantic = "DATETIME" if self._has_time_component(parsed) else "DATE"
                return semantic, 0.92, f"Nome temporale e {valid_ratio:.0%} valori parsabili come data/datetime."

        if any(term in normalized for term in self.IDENTIFIER_TERMS):
            return "IDENTIFIER", 0.95, "Nome colonna riconducibile a identificativo tecnico."

        if pd.api.types.is_bool_dtype(series):
            return "BOOLEAN", 0.98, "dtype booleano."
        values = {str(value).strip().lower() for value in series.dropna().unique()[:8]}
        if values and values.issubset(self.BOOLEAN_VALUES):
            return "BOOLEAN", 0.9, "Valori compatibili con boolean."
        if any(term in normalized for term in self.STATUS_TERMS):
            return "STATUS", 0.9, "Nome colonna riconducibile a stato/esito."
        if any(term in normalized for term in self.AMOUNT_TERMS):
            return "AMOUNT", 0.88, "Nome colonna riconducibile a importo."

        if pd.api.types.is_datetime64_any_dtype(series):
            return "DATETIME", 0.9, "dtype datetime."
        if pd.api.types.is_numeric_dtype(series):
            if row_count >= 10 and unique_ratio >= 0.95:
                return "IDENTIFIER", 0.78, "Colonna numerica ad alta unicita compatibile con ID."
            return "METRIC", 0.75, "Colonna numerica non identificativa."

        if 2 <= distinct_count <= min(50, max(10, int(row_count * 0.5))):
            return "CATEGORY", 0.75, "Cardinalita adatta a segmentazione."
        if distinct_count > min(50, max(10, int(row_count * 0.5))):
            return "CODE", 0.65, "Alta cardinalita testuale senza parsing data significativo."
        return "UNKNOWN", 0.4, "Nessuna regola semantica forte applicabile."

    def _parse_datetime_candidate(self, series: pd.Series) -> pd.Series:
        values = series.copy()
        if pd.api.types.is_numeric_dtype(values):
            numeric = pd.to_numeric(values, errors="coerce")
            compact = self._numeric_compact_dates(numeric)
            compact_valid = compact.dropna()
            compact_ratio = (
                float(compact_valid.str.len().isin([8, 14]).mean())
                if not compact_valid.empty
                else 0.0
            )
            if compact_ratio >= 0.5:
                return self._parse_compact_datetime(compact)
            numeric_valid = numeric.dropna()
            excel_ratio = (
                float(numeric_valid.between(20000, 60000).mean())
                if not numeric_valid.empty
                else 0.0
            )
            if excel_ratio >= 0.5:
                return pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
        return pd.to_datetime(values, errors="coerce")

    def _numeric_compact_dates(self, numeric: pd.Series) -> pd.Series:
        def convert(value):
            if pd.isna(value) or not np.isfinite(float(value)):
                return pd.NA
            float_value = float(value)
            if not float_value.is_integer():
                return pd.NA
            text = str(int(float_value))
            return text if len(text) in {8, 14} else pd.NA

        return numeric.map(convert).astype("string")

    def _parse_compact_datetime(self, compact: pd.Series) -> pd.Series:
        parsed = pd.Series(pd.NaT, index=compact.index, dtype="datetime64[ns]")
        date_mask = compact.str.len().eq(8).fillna(False)
        datetime_mask = compact.str.len().eq(14).fillna(False)
        if date_mask.any():
            parsed.loc[date_mask] = pd.to_datetime(
                compact.loc[date_mask],
                format="%Y%m%d",
                errors="coerce",
            )
        if datetime_mask.any():
            parsed.loc[datetime_mask] = pd.to_datetime(
                compact.loc[datetime_mask],
                format="%Y%m%d%H%M%S",
                errors="coerce",
            )
        return parsed

    def _has_time_component(self, parsed: pd.Series) -> bool:
        valid = parsed.dropna()
        if valid.empty:
            return False
        return bool((valid.dt.hour + valid.dt.minute + valid.dt.second).gt(0).mean() >= 0.1)

    def _normalize(self, value) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())
