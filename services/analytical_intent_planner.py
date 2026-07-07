"""Planner deterministico dell'intento analitico business."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd


class AnalyticalIntentPlanner:
    """Traduce richiesta e semantica colonne in un piano eseguibile JSON-safe."""

    ACTIVATION_METRIC = "TEMPO_ATTIVAZIONE_GIORNI"
    TECHNICAL_TERMS = {
        "id",
        "pyid",
        "contrattoid",
        "idcontratto",
        "idcontrattotlm",
        "serialnumber",
        "codicefiscale",
        "uuid",
        "guid",
        "key",
        "pzinskey",
    }
    DELIVERY_VALUES = {
        "consegna a mano": "CONSEGNA_A_MANO",
        "consegna_a_mano": "CONSEGNA_A_MANO",
        "mano": "CONSEGNA_A_MANO",
        "domicilio": "DOMICILIO",
        "agenzia": "RITIRO_IN_AGENZIA",
        "ritiro in agenzia": "RITIRO_IN_AGENZIA",
        "ritiro_in_agenzia": "RITIRO_IN_AGENZIA",
    }

    def build_plan(
        self,
        user_request: str,
        df: pd.DataFrame,
        semantic_feature_results: dict | None = None,
        semantic_columns: dict | None = None,
        domain_pack_context: dict | None = None,
    ) -> dict:
        request = str(user_request or "").lower()
        columns = list(df.columns) if isinstance(df, pd.DataFrame) else []
        semantic = semantic_columns if isinstance(semantic_columns, dict) else {}
        forbidden_columns = self._forbidden_columns(columns, semantic)
        has_activation_metric = self.ACTIVATION_METRIC in columns or self.ACTIVATION_METRIC in (
            semantic_feature_results or {}
        ).get("engineered_features", [])
        activation_request = any(
            term in request
            for term in (
                "tempo di attivazione",
                "tempi di attivazione",
                "attivazione",
                "durata attivazione",
                "sottoscrizione",
                "creazione antenna",
            )
        )

        primary_metric = None
        if has_activation_metric and activation_request:
            primary_metric = self.ACTIVATION_METRIC
        else:
            primary_metric = self._first_business_metric(df, columns, semantic, forbidden_columns)

        time_axis = self._preferred_column(
            columns,
            [
                "DATASOTTOSCRIZIONE_ADJUSTED",
                "DATA_SOTTOSCRIZIONE_ADJUSTED",
                "DATASOTTOSCRIZIONE",
                "DATA_SOTTOSCRIZIONE",
                "SOTTOSCRIZIONE",
            ],
            semantic,
            {"DATE", "DATETIME"},
        )
        event_axis = self._preferred_column(
            columns,
            ["CREAZIONE_ANTENNA", "DATA_CREAZIONE_ANTENNA", "CREAZIONEANTENNA"],
            semantic,
            {"DATE", "DATETIME"},
        )
        if not time_axis:
            time_axis = self._first_semantic_column(semantic, {"DATE", "DATETIME"}, forbidden_columns)
        if event_axis == time_axis:
            event_axis = None

        segmentations = []
        delivery = self._preferred_column(
            columns,
            ["METODOCONSEGNA", "METODO_CONSEGNA", "DELIVERY_METHOD"],
            semantic,
            {"CATEGORY", "STATUS"},
        )
        if delivery and delivery not in forbidden_columns:
            segmentations.append(delivery)
        for column, meta in semantic.items():
            if len(segmentations) >= 3:
                break
            if column in segmentations or column in forbidden_columns:
                continue
            if meta.get("semantic_type") in {"CATEGORY", "STATUS", "BOOLEAN"}:
                segmentations.append(column)

        temporal_concentration = any(
            term in request
            for term in ("giornate specifiche", "giorni specifici", "giornata", "giorno", "concentrati")
        )
        required_analyses = ["distribution", "percentiles", "outliers"]
        if temporal_concentration:
            required_analyses.append("temporal_concentration")
        if delivery:
            required_analyses.append("segmentation_by_delivery_method")

        excluded_analyses = [
            {
                "analysis": analysis,
                "column": column,
                "reason": "identifier",
            }
            for column in forbidden_columns
            for analysis in ("top_values", "correlation", "trend", "segmentation")
        ]

        return self._json_safe({
            "status": "computed",
            "intent_type": "activation_time_analysis" if primary_metric == self.ACTIVATION_METRIC else "general_analysis",
            "primary_metric": primary_metric,
            "time_axis": time_axis,
            "event_axis": event_axis,
            "segmentations": segmentations,
            "forbidden_columns": forbidden_columns,
            "required_analyses": required_analyses,
            "excluded_analyses": excluded_analyses,
            "temporal_concentration": temporal_concentration,
            "domain_pack_id": (
                domain_pack_context or {}
            ).get("pack_id") or ((domain_pack_context or {}).get("suggestion") or {}).get("pack_id"),
            "confidence": 0.9 if primary_metric == self.ACTIVATION_METRIC else 0.65,
        })

    def build_analysis_plan(self, intent_plan: dict) -> dict:
        """Converte intent plan in piano semplice per AnalysisEngine."""
        plan = intent_plan if isinstance(intent_plan, dict) else {}
        if plan.get("primary_metric") == self.ACTIVATION_METRIC and plan.get("time_axis"):
            return {
                "analysis_type": "time_trend",
                "target_column": None,
                "group_by_column": None,
                "value_column": self.ACTIVATION_METRIC,
                "time_column": plan.get("time_axis"),
                "aggregation": "mean",
                "limit": 10,
                "description": "Trend dei tempi di attivazione per data sottoscrizione.",
            }
        metric = plan.get("primary_metric")
        if metric:
            return {
                "analysis_type": "numeric_aggregation",
                "target_column": None,
                "group_by_column": None,
                "value_column": metric,
                "time_column": None,
                "aggregation": "mean",
                "limit": 10,
                "description": "Aggregazione della metrica primaria scelta dall'intent planner.",
            }
        return {}

    def temporal_concentration(
        self,
        df: pd.DataFrame,
        primary_metric: str,
        time_axis: str,
    ) -> dict:
        if (
            not isinstance(df, pd.DataFrame)
            or df.empty
            or primary_metric not in df.columns
            or time_axis not in df.columns
        ):
            return {
                "status": "skipped",
                "reason": "missing_metric_or_time_axis",
                "metric": primary_metric,
                "time_axis": time_axis,
            }

        metric = pd.to_numeric(df[primary_metric], errors="coerce")
        dates = pd.to_datetime(df[time_axis], errors="coerce")
        valid = pd.DataFrame({"metric": metric, "day": dates.dt.date}).dropna()
        if len(valid) < 5:
            return {
                "status": "insufficient_evidence",
                "metric": primary_metric,
                "time_axis": time_axis,
                "outlier_count": 0,
                "top_days": [],
                "conclusion": "insufficient_evidence",
            }

        q1 = float(valid["metric"].quantile(0.25))
        q3 = float(valid["metric"].quantile(0.75))
        iqr_threshold = q3 + 1.5 * (q3 - q1)
        p95_threshold = float(valid["metric"].quantile(0.95))
        threshold = min(p95_threshold, iqr_threshold) if iqr_threshold > q3 else p95_threshold
        outliers = valid[valid["metric"] >= threshold]
        if outliers.empty:
            return {
                "status": "computed",
                "metric": primary_metric,
                "time_axis": time_axis,
                "outlier_threshold": round(threshold, 4),
                "outlier_count": 0,
                "top_days": [],
                "conclusion": "insufficient_evidence",
            }

        daily_total = valid.groupby("day").size()
        daily_outliers = outliers.groupby("day").size().sort_values(ascending=False)
        top_days = []
        for day, count in daily_outliers.head(10).items():
            total = int(daily_total.loc[day])
            top_days.append({
                "day": str(day),
                "outlier_count": int(count),
                "total_count": total,
                "outlier_ratio": round(float(count) / total, 4) if total else 0.0,
            })

        top_outlier_share = float(daily_outliers.iloc[0]) / max(1, int(len(outliers)))
        conclusion = "concentrated" if top_outlier_share >= 0.5 else "distributed"
        return self._json_safe({
            "status": "computed",
            "metric": primary_metric,
            "time_axis": time_axis,
            "outlier_threshold": round(threshold, 4),
            "outlier_count": int(len(outliers)),
            "top_days": top_days,
            "conclusion": conclusion,
        })

    def parse_followup_filter(self, user_message: str, df: pd.DataFrame) -> dict | None:
        message = str(user_message or "").lower()
        filter_terms = (
            "solo record che hanno",
            "usando solo record con",
            "solo record con",
            "filtra per",
            "limitati a",
            "solo quelli con",
            "solo i record",
            "per i soli record",
        )
        if not any(term in message for term in filter_terms):
            return None
        column = self._preferred_column(
            list(df.columns) if isinstance(df, pd.DataFrame) else [],
            ["METODOCONSEGNA", "METODO_CONSEGNA", "DELIVERY_METHOD"],
            {},
            set(),
        )
        if not column:
            return None
        for phrase, normalized_value in self.DELIVERY_VALUES.items():
            if phrase in message:
                return {
                    "column": column,
                    "operator": "==",
                    "value": normalized_value,
                    "source_phrase": phrase,
                }
        return None

    def apply_followup_filter(self, df: pd.DataFrame, filter_spec: dict) -> pd.DataFrame:
        column = filter_spec.get("column") if isinstance(filter_spec, dict) else None
        value = filter_spec.get("value") if isinstance(filter_spec, dict) else None
        if not isinstance(df, pd.DataFrame) or column not in df.columns or value is None:
            return pd.DataFrame()
        normalized = df[column].map(self._normalize_value)
        return df.loc[normalized == str(value).upper()].copy()

    def _forbidden_columns(self, columns: list, semantic_columns: dict) -> list[str]:
        forbidden = []
        for column in columns:
            normalized = self._normalize(str(column))
            semantic_type = (semantic_columns.get(str(column)) or {}).get("semantic_type")
            if semantic_type in {"IDENTIFIER", "CODE", "EMAIL", "PHONE"} or any(
                term in normalized for term in self.TECHNICAL_TERMS
            ):
                forbidden.append(str(column))
        return list(dict.fromkeys(forbidden))

    def _first_business_metric(
        self,
        df: pd.DataFrame,
        columns: list,
        semantic_columns: dict,
        forbidden: list[str],
    ) -> str | None:
        for column in columns:
            if str(column) in forbidden:
                continue
            if not isinstance(df, pd.DataFrame) or not pd.api.types.is_numeric_dtype(df[column]):
                continue
            if (semantic_columns.get(str(column)) or {}).get("semantic_type") in {
                "METRIC",
                "AMOUNT",
                "PERCENTAGE",
                "DURATION",
            }:
                return str(column)
        return None

    def _first_semantic_column(self, semantic_columns: dict, allowed: set[str], forbidden: list[str]) -> str | None:
        for column, meta in semantic_columns.items():
            if column not in forbidden and meta.get("semantic_type") in allowed:
                return column
        return None

    def _preferred_column(
        self,
        columns: list,
        preferred_names: list[str],
        semantic_columns: dict,
        allowed_types: set[str],
    ) -> str | None:
        normalized = {str(column): self._normalize(str(column)) for column in columns}
        preferred = [self._normalize(name) for name in preferred_names]
        for preferred_name in preferred:
            for column, column_normalized in normalized.items():
                if column_normalized == preferred_name or preferred_name in column_normalized:
                    if not allowed_types or (semantic_columns.get(column) or {}).get("semantic_type") in allowed_types:
                        return column
        for column, column_normalized in normalized.items():
            if any(column_normalized in preferred_name for preferred_name in preferred):
                if not allowed_types or (semantic_columns.get(column) or {}).get("semantic_type") in allowed_types:
                    return column
        return None

    def _normalize_value(self, value: Any) -> str:
        text = str(value or "").strip().upper()
        text = re.sub(r"[^A-Z0-9]+", "_", text).strip("_")
        aliases = {
            "CONSEGNA_A_MANO": "CONSEGNA_A_MANO",
            "CONSEGNA_MANO": "CONSEGNA_A_MANO",
            "A_MANO": "CONSEGNA_A_MANO",
            "DOMICILIO": "DOMICILIO",
            "RITIRO_AGENZIA": "RITIRO_IN_AGENZIA",
            "RITIRO_IN_AGENZIA": "RITIRO_IN_AGENZIA",
        }
        return aliases.get(text, text)

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        return value
