"""Semantic Feature Engineering Engine per feature analitiche derivate."""

from __future__ import annotations

from typing import Any
import re

import numpy as np
import pandas as pd

from utils.logging_config import get_logger


logger = get_logger("semantic_feature_engineering")


class SemanticFeatureEngineeringEngine:
    """Crea feature derivate richieste dall'utente senza mutare il dataframe originale."""

    ACTIVATION_OUTPUT = "TEMPO_ATTIVAZIONE_GIORNI"
    START_TERMS = {
        "datasottoscrizione",
        "datasottoscrizione",
        "sottoscrizione",
        "subscriptiondate",
        "startdate",
        "datainizio",
    }
    END_TERMS = {
        "creazioneantenna",
        "datacreazioneantenna",
        "antenna creation",
        "activationdate",
        "enddate",
        "createdat",
        "creazione",
    }

    def build_feature_plan(
        self,
        user_request: str,
        df,
        semantic_columns: dict | list | None = None,
        domain_pack_context: dict | None = None,
        analytical_execution_plan: dict | None = None,
    ) -> dict:
        requested = self.infer_requested_features(user_request, domain_pack_context)
        features = []
        warnings = []
        for feature in requested:
            logger.info("Feature requested: %s", feature.get("feature_name"))
            mapping = self.map_source_columns(df, feature, semantic_columns, analytical_execution_plan)
            logger.info(
                "Feature source columns mapped: feature=%s start=%s end=%s",
                feature.get("feature_name"),
                mapping.get("start"),
                mapping.get("end"),
            )
            status = "planned" if mapping.get("start") and mapping.get("end") else "missing_sources"
            if status != "planned":
                warnings.append({
                    "feature_name": feature["feature_name"],
                    "warning": "source_columns_missing",
                    "mapping": mapping,
                })
            features.append({
                **feature,
                "status": status,
                "source_columns": mapping,
            })
        return {
            "status": "computed",
            "requested_features": requested,
            "features": features,
            "warnings": warnings,
        }

    def apply_feature_plan(self, df, feature_plan: dict) -> tuple[pd.DataFrame, dict]:
        enriched = df.copy()
        results = {
            "status": "computed",
            "features": [],
            "engineered_features": [],
            "warnings": [],
        }
        for feature in feature_plan.get("features", []) or []:
            if feature.get("feature_type") != "DURATION" or feature.get("status") != "planned":
                continue
            sources = feature.get("source_columns") or {}
            start = sources.get("start")
            end = sources.get("end")
            output = feature.get("feature_name", self.ACTIVATION_OUTPUT)
            if start not in enriched.columns or end not in enriched.columns:
                results["warnings"].append({
                    "feature_name": output,
                    "warning": "source_column_not_available",
                    "source_columns": sources,
                })
                continue
            try:
                start_parsed = self.parse_datetime_series(enriched[start])
                end_parsed = self.parse_datetime_series(enriched[end])
                duration = self._duration_from_parsed(
                    start_parsed,
                    end_parsed,
                    unit=feature.get("unit", "days"),
                )
            except Exception as exc:
                logger.warning(
                    "Feature creation skipped: feature=%s error=%s",
                    output,
                    type(exc).__name__,
                )
                results["warnings"].append({
                    "feature_name": output,
                    "warning": "feature_creation_error",
                    "error": str(exc),
                })
                continue
            enriched[output] = duration.astype("float64")
            invalid_start = int(start_parsed.isna().sum())
            invalid_end = int(end_parsed.isna().sum())
            negative_count = int((duration < 0).sum())
            if negative_count:
                results["warnings"].append({
                    "feature_name": output,
                    "warning": "negative_duration",
                    "count": negative_count,
                })
            feature_result = {
                "feature_name": output,
                "feature_type": "DURATION",
                "status": "created",
                "source_columns": {"start": start, "end": end},
                "unit": feature.get("unit", "days"),
                "valid_count": int(duration.notna().sum()),
                "missing_count": int(duration.isna().sum()),
                "negative_duration_count": negative_count,
                "parse_errors": {
                    "start": invalid_start,
                    "end": invalid_end,
                },
                "recommended_analysis": list(feature.get("recommended_analysis", [])),
            }
            results["features"].append(feature_result)
            results["engineered_features"].append(output)
            logger.info(
                "Feature created: feature=%s parsed_start_valid=%s parsed_end_valid=%s valid_count=%s missing_count=%s negative_duration_count=%s",
                output,
                int(start_parsed.notna().sum()),
                int(end_parsed.notna().sum()),
                feature_result["valid_count"],
                feature_result["missing_count"],
                negative_count,
            )
        return enriched, results

    def infer_requested_features(
        self,
        user_request: str,
        domain_pack_context: dict | None = None,
    ) -> list[dict]:
        request = (user_request or "").lower()
        activation_terms = [
            "tempo di attivazione",
            "tempi di attivazione",
            "distribuzione tempi",
            "activation time",
            "durata attivazione",
            "giorni attivazione",
            "sottoscrizione",
            "creazione antenna",
        ]
        if any(term in request for term in activation_terms):
            return [{
                "feature_name": self.ACTIVATION_OUTPUT,
                "feature_type": "DURATION",
                "logical_name": "activation_time",
                "unit": "days",
                "recommended_analysis": [
                    "distribution",
                    "percentiles",
                    "outliers",
                    "trend_by_start_date",
                    "trend_by_end_date",
                    "group_by_category",
                    "sla_threshold",
                ],
            }]
        return []

    def map_source_columns(
        self,
        df,
        requested_feature: dict,
        semantic_columns: dict | list | None = None,
        analytical_execution_plan: dict | None = None,
    ) -> dict:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {"start": None, "end": None}
        columns = list(df.columns)
        start = self._best_column(columns, self.START_TERMS)
        end = self._best_column(columns, self.END_TERMS)
        if start is None:
            start = self._date_column_by_keyword(df, ["sottoscrizione", "subscription", "start", "inizio"])
        if end is None:
            end = self._date_column_by_keyword(df, ["creazione", "antenna", "activation", "created", "end", "fine"])
        adjusted_start = self._adjusted_source_column(start, analytical_execution_plan, columns)
        if adjusted_start:
            start = adjusted_start
        return {"start": start, "end": end}

    def _adjusted_source_column(
        self,
        start: str | None,
        analytical_execution_plan: dict | None,
        columns: list,
    ) -> str | None:
        if not start or not isinstance(analytical_execution_plan, dict):
            return None
        feature_requirements = analytical_execution_plan.get("feature_requirements") or []
        if not any(item.get("use_adjusted_source") for item in feature_requirements):
            return None
        for transformation in analytical_execution_plan.get("transformations") or []:
            if transformation.get("source_column") != start:
                continue
            output = transformation.get("output_column")
            if output in columns:
                return output
        candidate = f"{start}_ADJUSTED"
        return candidate if candidate in columns else None

    def parse_datetime_series(self, series: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.to_datetime(series, errors="coerce")
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            return self._parse_numeric_datetime(numeric)

        parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        numeric = pd.to_numeric(series, errors="coerce")
        text_values = series.astype("string")

        compact = text_values.str.replace(r"\D", "", regex=True)
        compact = compact.mask(compact.str.len() == 0)
        compact_mask = compact.str.len().isin([8, 14]).fillna(False)
        if compact_mask.any():
            parsed.loc[compact_mask] = self._parse_compact_datetime(compact.loc[compact_mask])

        excel_mask = numeric.between(20000, 60000).fillna(False) & parsed.isna()
        if excel_mask.any():
            parsed.loc[excel_mask] = pd.to_datetime(
                numeric.loc[excel_mask],
                unit="D",
                origin="1899-12-30",
                errors="coerce",
            )

        generic_mask = parsed.isna() & numeric.isna()
        if generic_mask.any():
            parsed.loc[generic_mask] = pd.to_datetime(
                series.loc[generic_mask],
                errors="coerce",
            )
        return parsed

    def create_duration_feature(
        self,
        df,
        start_column: str,
        end_column: str,
        output_column: str,
        unit: str = "days",
    ) -> pd.Series:
        start = self.parse_datetime_series(df[start_column])
        end = self.parse_datetime_series(df[end_column])
        return self._duration_from_parsed(start, end, unit=unit)

    def _duration_from_parsed(
        self,
        start: pd.Series,
        end: pd.Series,
        unit: str = "days",
    ) -> pd.Series:
        delta = end - start
        if unit == "hours":
            return delta.dt.total_seconds() / 3600
        return delta.dt.total_seconds() / 86400

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

    def _parse_numeric_datetime(self, numeric: pd.Series) -> pd.Series:
        compact = self._numeric_compact_dates(numeric)
        compact_valid = compact.dropna()
        if not compact_valid.empty and compact_valid.str.len().isin([8, 14]).mean() >= 0.5:
            return self._parse_compact_datetime(compact)
        if numeric.dropna().between(20000, 60000).mean() >= 0.5:
            return pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
        return pd.to_datetime(numeric, errors="coerce")

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

    def export_feature_summary(self, feature_results: dict) -> dict:
        features = feature_results.get("features") or []
        return {
            "status": feature_results.get("status", "unknown"),
            "feature_count": len(features),
            "engineered_features": list(feature_results.get("engineered_features") or []),
            "warnings": list(feature_results.get("warnings") or []),
        }

    def _best_column(self, columns: list, terms: set[str]) -> str | None:
        normalized = {column: self._normalize(column) for column in columns}
        for column, name in normalized.items():
            if name in terms or any(term in name for term in terms):
                return column
        return None

    def _date_column_by_keyword(self, df: pd.DataFrame, keywords: list[str]) -> str | None:
        for column in df.columns:
            name = self._normalize(column)
            if not any(self._normalize(keyword) in name for keyword in keywords):
                continue
            parsed = self.parse_datetime_series(df[column])
            if parsed.notna().sum() >= max(2, int(len(df) * 0.3)):
                return column
        return None

    def _normalize(self, value) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())
