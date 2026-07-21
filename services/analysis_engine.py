"""Motore deterministico per piani analitici Pandas.

L'LLM puo aiutare a interpretare la richiesta, ma questo modulo esegue i
calcoli reali sul dataframe e restituisce solo risultati serializzabili.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AnalysisPlan:
    """Piano analitico semplice e serializzabile."""

    analysis_type: str
    target_column: str | None = None
    group_by_column: str | None = None
    value_column: str | None = None
    time_column: str | None = None
    aggregation: str | None = None
    limit: int | None = None
    related_columns: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisPlan":
        valid_keys = set(cls.__dataclass_fields__.keys())
        values = {key: data.get(key) for key in valid_keys}
        values["related_columns"] = list(values.get("related_columns") or [])
        return cls(**values)


class AnalysisEngine:
    """Interpreta piani analitici semplici ed esegue calcoli Pandas reali."""

    SUPPORTED_ANALYSES = {
        "count_occurrences",
        "top_n",
        "numeric_aggregation",
        "time_trend",
        "null_detection",
        "duplicate_detection",
    }

    def __init__(self, history_manager=None):
        self.history_manager = history_manager

    def run(
        self,
        user_request: str,
        df: pd.DataFrame,
        source_type: str = "unknown",
        plan: AnalysisPlan | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Costruisce o riceve un piano, lo esegue e ritorna un payload JSON-safe."""
        if not isinstance(df, pd.DataFrame) or df.empty:
            empty_plan = plan or AnalysisPlan(
                analysis_type="null_detection",
                description="Nessun dataframe disponibile.",
            )
            if isinstance(empty_plan, dict):
                empty_plan = AnalysisPlan.from_dict(empty_plan)
            return {
                "analysis_plan": empty_plan.to_dict(),
                "deterministic_results": {
                    "status": "empty",
                    "message": "Nessun dataframe disponibile per l'analisi deterministica.",
                },
                "execution_summary": {
                    "status": "skipped",
                    "source": "analysis_engine",
                    "row_count": 0,
                    "columns_used": [],
                    "analysis_pattern_id": None,
                    "plan_source": "new",
                    "confidence_score": 0.0,
                    "similarity_score": None,
                    "similarity_method": None,
                },
                "analysis_pattern_id": None,
                "plan_source": "new",
                "confidence_score": 0.0,
                "similarity_score": None,
                "similarity_method": None,
            }

        selected_plan, plan_metadata = self._coerce_or_infer_plan(user_request, df, source_type, plan)
        results = self.execute_plan(df, selected_plan)
        columns_used = self._columns_used(selected_plan)
        if plan_metadata["plan_source"] == "new":
            saved_pattern = self._save_pattern(user_request, source_type, selected_plan, columns_used)
            if saved_pattern:
                plan_metadata["analysis_pattern_id"] = saved_pattern["id"]
                plan_metadata["confidence_score"] = saved_pattern["confidence_score"]

        results["plan_source"] = plan_metadata["plan_source"]
        results["analysis_pattern_id"] = plan_metadata["analysis_pattern_id"]
        results["confidence_score"] = plan_metadata["confidence_score"]
        results["similarity_score"] = plan_metadata["similarity_score"]
        results["similarity_method"] = plan_metadata["similarity_method"]
        summary = {
            "status": "completed",
            "source": "analysis_engine",
            "plan_source": plan_metadata["plan_source"],
            "analysis_type": selected_plan.analysis_type,
            "row_count": int(len(df)),
            "columns_used": columns_used,
            "analysis_pattern_id": plan_metadata["analysis_pattern_id"],
            "confidence_score": plan_metadata["confidence_score"],
            "similarity_score": plan_metadata["similarity_score"],
            "similarity_method": plan_metadata["similarity_method"],
        }

        return {
            "analysis_plan": selected_plan.to_dict(),
            "deterministic_results": results,
            "execution_summary": summary,
            "analysis_pattern_id": plan_metadata["analysis_pattern_id"],
            "plan_source": plan_metadata["plan_source"],
            "confidence_score": plan_metadata["confidence_score"],
            "similarity_score": plan_metadata["similarity_score"],
            "similarity_method": plan_metadata["similarity_method"],
        }

    def infer_plan(self, user_request: str, df: pd.DataFrame, source_type: str = "unknown") -> AnalysisPlan:
        """Inferisce un piano semplice usando richiesta, schema dataframe e history."""
        plan, _ = self._infer_plan_with_metadata(user_request, df, source_type)
        return plan

    def execute_plan(self, df: pd.DataFrame, plan: AnalysisPlan | dict[str, Any]) -> dict[str, Any]:
        """Esegue il piano sul dataframe."""
        if isinstance(plan, dict):
            plan = AnalysisPlan.from_dict(plan)

        if plan.analysis_type not in self.SUPPORTED_ANALYSES:
            raise ValueError(f"Tipo analisi non supportato: {plan.analysis_type}")

        handlers = {
            "count_occurrences": self._count_occurrences,
            "top_n": self._top_n,
            "numeric_aggregation": self._numeric_aggregation,
            "time_trend": self._time_trend,
            "null_detection": self._null_detection,
            "duplicate_detection": self._duplicate_detection,
        }
        result = handlers[plan.analysis_type](df, plan)
        result["analysis_type"] = plan.analysis_type
        result["plan"] = plan.to_dict()
        result.setdefault("status", "computed")
        return self._json_safe(result)

    def _coerce_or_infer_plan(self, user_request, df, source_type, plan):
        if plan is None:
            return self._infer_plan_with_metadata(user_request, df, source_type)
        if isinstance(plan, AnalysisPlan):
            return plan, self._new_plan_metadata()
        return AnalysisPlan.from_dict(plan), self._new_plan_metadata()

    def _infer_plan_with_metadata(self, user_request: str, df: pd.DataFrame, source_type: str):
        historical = self._find_reusable_plan(user_request, source_type)
        if historical:
            plan = AnalysisPlan.from_dict(historical["analysis_plan"])
            plan.description = plan.description or historical.get("description", "")
            return plan, {
                "analysis_pattern_id": historical["id"],
                "plan_source": "history",
                "confidence_score": historical.get("confidence_score", 0.0),
                "similarity_score": historical.get("similarity_score", historical.get("similarity")),
                "similarity_method": historical.get("similarity_method", "text"),
            }
        return self._infer_new_plan(user_request, df), self._new_plan_metadata()

    def _infer_new_plan(self, user_request: str, df: pd.DataFrame) -> AnalysisPlan:
        request = (user_request or "").lower()
        limit = self._extract_limit(request) or 10

        if any(term in request for term in ["null", "nullo", "nulli", "mancant", "missing"]):
            return AnalysisPlan(
                analysis_type="null_detection",
                limit=limit,
                description="Rilevazione valori nulli nel dataframe.",
            )

        if any(term in request for term in ["duplicat", "doppion"]):
            return AnalysisPlan(
                analysis_type="duplicate_detection",
                limit=limit,
                description="Rilevazione righe duplicate nel dataframe.",
            )

        if any(term in request for term in ["trend", "andamento", "tempo", "mese", "giorno", "settimana"]):
            time_column = self._find_datetime_column(df, request)
            value_column = self._find_numeric_column(df, request)
            return AnalysisPlan(
                analysis_type="time_trend",
                time_column=time_column,
                value_column=value_column,
                aggregation=self._find_aggregation(request) or ("sum" if value_column else "count"),
                limit=limit,
                description="Trend temporale calcolato dal dataframe.",
            )

        if any(term in request for term in ["top", "miglior", "peggior", "classifica", "ranking", "primi"]):
            return AnalysisPlan(
                analysis_type="top_n",
                target_column=self._find_categorical_column(df, request),
                value_column=self._find_numeric_column(df, request),
                aggregation=self._find_aggregation(request) or "count",
                limit=limit,
                description=f"Top {limit} valori calcolati dal dataframe.",
            )

        count_terms = ["conteggio", "occorren", "quanti", "numero", "totale", "distribuzione"]
        if any(term in request for term in count_terms):
            ranked = self._rank_categorical_columns(df, request)
            return AnalysisPlan(
                analysis_type="count_occurrences",
                target_column=ranked[0] if ranked else self._find_categorical_column(df, request),
                related_columns=ranked[1:4],
                limit=limit,
                description="Conteggio occorrenze calcolato dal dataframe.",
            )

        aggregation = self._find_aggregation(request)
        if aggregation:
            return AnalysisPlan(
                analysis_type="numeric_aggregation",
                group_by_column=self._find_categorical_column(df, request),
                value_column=self._find_numeric_column(df, request),
                aggregation=aggregation,
                limit=limit,
                description=f"Aggregazione numerica '{aggregation}' calcolata dal dataframe.",
            )

        return AnalysisPlan(
            analysis_type="count_occurrences",
            target_column=self._find_categorical_column(df, request),
            limit=limit,
            description="Piano fallback: conteggio della prima colonna categoriale utile.",
        )

    def _new_plan_metadata(self):
        return {
            "analysis_pattern_id": None,
            "plan_source": "new",
            "confidence_score": 0.0,
            "similarity_score": None,
            "similarity_method": None,
        }

    def _count_occurrences(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        column = self._require_column(df, plan.target_column or self._find_categorical_column(df, ""))
        limit = plan.limit or 10
        counts = df[column].fillna("N/D").astype(str).value_counts(dropna=False).head(limit)
        related_counts = []
        for related in plan.related_columns or []:
            if related == column or related not in df.columns:
                continue
            values = df[related].fillna("N/D").astype(str).value_counts(dropna=False).head(limit)
            related_counts.append({
                "target_column": str(related),
                "counts": [
                    {"value": self._json_safe(index), "count": int(value)}
                    for index, value in values.items()
                ],
                "unique_values": int(df[related].nunique(dropna=True)),
            })
        return {
            "target_column": str(column),
            "total_records": int(len(df)),
            "counts": [
                {"value": self._json_safe(index), "count": int(value)}
                for index, value in counts.items()
            ],
            "unique_values": int(df[column].nunique(dropna=True)),
            "related_counts": related_counts,
        }

    def _top_n(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        target = self._require_column(df, plan.target_column or self._find_categorical_column(df, ""))
        limit = plan.limit or 10
        aggregation = plan.aggregation or "count"

        if plan.value_column and plan.value_column in df.columns and aggregation != "count":
            value = self._require_numeric_column(df, plan.value_column)
            grouped = self._aggregate_grouped(df, target, value, aggregation)
            top = grouped.sort_values(ascending=False).head(limit)
            return {
                "target_column": str(target),
                "value_column": str(value),
                "aggregation": aggregation,
                "top": [
                    {"value": self._json_safe(index), "metric": self._json_safe(metric)}
                    for index, metric in top.items()
                ],
            }

        counts = df[target].fillna("N/D").astype(str).value_counts(dropna=False).head(limit)
        return {
            "target_column": str(target),
            "aggregation": "count",
            "top": [
                {"value": self._json_safe(index), "metric": int(metric)}
                for index, metric in counts.items()
            ],
        }

    def _numeric_aggregation(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        value = self._require_numeric_column(df, plan.value_column or self._find_numeric_column(df, ""))
        aggregation = plan.aggregation or "sum"
        group = plan.group_by_column if plan.group_by_column in df.columns else None

        if group:
            grouped = self._aggregate_grouped(df, group, value, aggregation)
            grouped = grouped.sort_values(ascending=False)
            if plan.limit:
                grouped = grouped.head(plan.limit)
            return {
                "value_column": str(value),
                "group_by_column": str(group),
                "aggregation": aggregation,
                "groups": [
                    {"group": self._json_safe(index), "value": self._json_safe(metric)}
                    for index, metric in grouped.items()
                ],
            }

        series = df[value].dropna()
        return {
            "value_column": str(value),
            "aggregation": aggregation,
            "result": self._json_safe(self._aggregate_series(series, aggregation)),
            "count": int(series.count()),
        }

    def _time_trend(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        time_column = self._require_column(df, plan.time_column or self._find_datetime_column(df, ""))
        parsed = pd.to_datetime(df[time_column], errors="coerce")
        valid = df.loc[parsed.notna()].copy()
        valid["_analysis_time"] = parsed.loc[parsed.notna()]
        if valid.empty:
            return {
                "time_column": str(time_column),
                "status": "empty",
                "points": [],
            }

        freq = self._choose_time_frequency(valid["_analysis_time"])
        aggregation = plan.aggregation or "count"
        value_column = plan.value_column if plan.value_column in valid.columns else None

        if value_column and aggregation != "count":
            value_column = self._require_numeric_column(valid, value_column)
            trend = valid.set_index("_analysis_time")[value_column].resample(freq).agg(aggregation).dropna()
        else:
            trend = valid.set_index("_analysis_time").resample(freq).size()
            aggregation = "count"

        return {
            "time_column": str(time_column),
            "value_column": str(value_column) if value_column else None,
            "aggregation": aggregation,
            "frequency": freq,
            "points": [
                {"period": index.isoformat(), "value": self._json_safe(value)}
                for index, value in trend.items()
            ],
        }

    def _null_detection(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        missing = df.isna().sum()
        percentages = (missing / len(df) * 100).round(2)
        columns = [
            {
                "column": str(column),
                "null_count": int(missing[column]),
                "null_percent": self._json_safe(percentages[column]),
            }
            for column in df.columns
            if int(missing[column]) > 0
        ]
        columns.sort(key=lambda item: item["null_count"], reverse=True)
        if plan.limit:
            columns = columns[:plan.limit]
        return {
            "row_count": int(len(df)),
            "columns_with_nulls": columns,
            "total_nulls": int(missing.sum()),
        }

    def _duplicate_detection(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        duplicate_mask = df.duplicated(keep=False)
        sample_limit = plan.limit or 5
        return {
            "row_count": int(len(df)),
            "duplicate_rows": int(df.duplicated().sum()),
            "duplicate_groups_rows": int(duplicate_mask.sum()),
            "sample": self._json_safe(
                df.loc[duplicate_mask].head(sample_limit).to_dict(orient="records")
            ),
        }

    def _save_pattern(self, user_request, source_type, plan, columns_used):
        if not self.history_manager:
            return None
        try:
            pattern_id = self.history_manager.add_pattern(
                description=user_request,
                source_type=source_type,
                analysis_plan=plan.to_dict(),
                columns_used=columns_used,
                feedback_score=0.0,
                success=False,
                notes="Pattern salvato automaticamente dopo esecuzione deterministica.",
            )
            return self.history_manager.get_pattern(pattern_id)
        except Exception:
            return None

    def _find_reusable_plan(self, user_request: str, source_type: str) -> dict[str, Any] | None:
        if not self.history_manager:
            return None
        matches = self.history_manager.find_similar_patterns(
            description=user_request,
            source_type=source_type,
            similarity_threshold=0.65,
            min_feedback_score=0.6,
        )
        if not matches:
            return None
        best = matches[0]
        try:
            self.history_manager.record_usage(best["id"])
            refreshed = self.history_manager.get_pattern(best["id"])
            if refreshed:
                best.update(refreshed)
        except Exception:
            pass
        return best

    def _extract_limit(self, request: str) -> int | None:
        patterns = [
            r"\btop\s+(\d+)\b",
            r"\bprimi\s+(\d+)\b",
            r"\bprime\s+(\d+)\b",
            r"\bultimi\s+(\d+)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, request)
            if match:
                return max(1, int(match.group(1)))
        return None

    def _find_aggregation(self, request: str) -> str | None:
        mapping = {
            "media": "mean",
            "medio": "mean",
            "average": "mean",
            "mean": "mean",
            "somma": "sum",
            "totale": "sum",
            "sum": "sum",
            "massimo": "max",
            "max": "max",
            "minimo": "min",
            "min": "min",
            "conteggio": "count",
            "count": "count",
        }
        for keyword, aggregation in mapping.items():
            if keyword in request:
                return aggregation
        return None

    def _find_categorical_column(self, df: pd.DataFrame, request: str) -> str | None:
        ranked = self._rank_categorical_columns(df, request)
        if ranked:
            return ranked[0]
        mentioned = self._find_mentioned_column(df, request)
        if mentioned and not pd.api.types.is_numeric_dtype(df[mentioned]) and not self._is_identifier_column(mentioned, df):
            return str(mentioned)

        categorical = [
            column for column in df.columns
            if (
                pd.api.types.is_object_dtype(df[column])
                or pd.api.types.is_string_dtype(df[column])
                or pd.api.types.is_bool_dtype(df[column])
                or isinstance(df[column].dtype, pd.CategoricalDtype)
            )
        ]
        low_cardinality = [
            column for column in categorical
            if 1 <= df[column].nunique(dropna=True) <= max(30, int(len(df) * 0.5))
        ]
        candidates = low_cardinality or categorical
        candidates = [
            column for column in candidates
            if not self._is_identifier_column(column, df)
        ]
        return str(candidates[0]) if candidates else None

    def _rank_categorical_columns(self, df: pd.DataFrame, request: str) -> list[str]:
        """Ordina le dimensioni business citate, tollerando singolare/plurale e underscore."""
        candidates = [
            column for column in df.columns
            if (
                pd.api.types.is_object_dtype(df[column])
                or pd.api.types.is_string_dtype(df[column])
                or pd.api.types.is_bool_dtype(df[column])
                or isinstance(df[column].dtype, pd.CategoricalDtype)
            ) and not self._is_identifier_column(column, df)
        ]
        request_tokens = self._semantic_tokens(request)
        active_intent = any(token.startswith("attiv") for token in request_tokens)
        scored = []
        for position, column in enumerate(candidates):
            column_tokens = self._semantic_tokens(str(column))
            matches = sum(
                1 for left in column_tokens for right in request_tokens
                if len(left) >= 4 and len(right) >= 4 and left[:5] == right[:5]
            )
            if active_intent and any(token.startswith("stato") for token in column_tokens):
                matches += 1
            if active_intent and any(token.startswith("contrat") for token in column_tokens):
                matches += 1
            cardinality = int(df[column].nunique(dropna=True))
            useful = 1 if 1 <= cardinality <= max(50, int(len(df) * 0.5)) else 0
            scored.append((matches, useful, -position, str(column)))
        scored.sort(reverse=True)
        matched = [item[3] for item in scored if item[0] > 0]
        fallback = [item[3] for item in scored if item[3] not in matched and item[1] > 0]
        return matched + fallback

    def _semantic_tokens(self, value: str) -> list[str]:
        return [token for token in self._normalize(value).split() if len(token) >= 3]

    def _find_numeric_column(self, df: pd.DataFrame, request: str) -> str | None:
        numeric_columns = [
            column for column in df.select_dtypes(include="number").columns
            if not self._is_identifier_column(column, df)
        ]
        for column in numeric_columns:
            if str(column).upper() == "TEMPO_ATTIVAZIONE_GIORNI":
                return str(column)
        mentioned = self._find_mentioned_column(df, request)
        if mentioned in numeric_columns:
            return str(mentioned)
        return str(numeric_columns[0]) if numeric_columns else None

    def _find_datetime_column(self, df: pd.DataFrame, request: str) -> str | None:
        datetime_columns = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
        mentioned = self._find_mentioned_column(df, request)
        if mentioned:
            parsed = pd.to_datetime(df[mentioned], errors="coerce")
            if parsed.notna().sum() >= max(1, int(len(df) * 0.2)):
                return str(mentioned)

        for column in datetime_columns:
            return str(column)

        for column in df.columns:
            normalized = str(column).lower().replace("_", " ")
            if any(term in normalized for term in [
                "date", "data", "time", "timestamp", "giorno", "mese",
                "sottoscrizione", "creazione", "antenna", "attivazione",
            ]):
                parsed = pd.to_datetime(df[column], errors="coerce")
                if parsed.notna().sum() >= max(1, int(len(df) * 0.2)):
                    return str(column)
        return None

    def _is_identifier_column(self, column, df: pd.DataFrame) -> bool:
        normalized = self._normalize(str(column)).replace(" ", "")
        id_terms = {
            "id",
            "pyid",
            "pzinskey",
            "uuid",
            "guid",
            "key",
            "idcontratto",
            "idcontrattotlm",
            "contrattoid",
            "serialnumber",
            "codicefiscale",
        }
        if normalized in id_terms or any(term in normalized for term in id_terms):
            return True
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]) and len(df) >= 10:
            unique_ratio = df[column].nunique(dropna=True) / max(1, df[column].dropna().shape[0])
            return unique_ratio >= 0.95
        return False

    def _find_mentioned_column(self, df: pd.DataFrame, request: str):
        normalized_request = self._normalize(request)
        for column in df.columns:
            normalized_column = self._normalize(str(column))
            if normalized_column and normalized_column in normalized_request:
                return column
        return None

    def _require_column(self, df: pd.DataFrame, column: str | None) -> str:
        if not column or column not in df.columns:
            raise ValueError(f"Colonna non disponibile per l'analisi: {column}")
        return column

    def _require_numeric_column(self, df: pd.DataFrame, column: str | None) -> str:
        column = self._require_column(df, column)
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"La colonna non e numerica: {column}")
        return column

    def _aggregate_grouped(self, df: pd.DataFrame, group_column: str, value_column: str, aggregation: str):
        grouped = df.groupby(group_column, dropna=False)[value_column]
        if aggregation == "count":
            return grouped.count()
        return grouped.agg(aggregation)

    def _aggregate_series(self, series: pd.Series, aggregation: str):
        if aggregation == "sum":
            return series.sum()
        if aggregation == "mean":
            return series.mean()
        if aggregation == "min":
            return series.min()
        if aggregation == "max":
            return series.max()
        if aggregation == "count":
            return series.count()
        raise ValueError(f"Aggregazione non supportata: {aggregation}")

    def _choose_time_frequency(self, series: pd.Series) -> str:
        span_days = max((series.max() - series.min()).days, 0)
        if span_days > 730:
            return "YE"
        if span_days > 90:
            return "ME"
        return "D"

    def _columns_used(self, plan: AnalysisPlan) -> list[str]:
        columns = [
            plan.target_column,
            plan.group_by_column,
            plan.value_column,
            plan.time_column,
            *(plan.related_columns or []),
        ]
        return [str(column) for column in columns if column]

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return value
