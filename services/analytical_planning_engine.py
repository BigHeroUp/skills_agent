"""Pianificazione analitica deterministica prima di feature/statistiche/report."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from utils.logging_config import get_logger


logger = get_logger("analytical_planning_engine")


class IntentParser:
    """Estrae intent analitico e trasformazioni richieste dal prompt utente."""

    def parse(self, user_request: str) -> dict[str, Any]:
        request = (user_request or "").lower()
        transformations = []
        shift_match = re.search(r"(aggiungi|somma|\+)\s*(?:\+)?\s*(\d+)\s*h|aggiungi un'?ora", request)
        subtract_match = re.search(r"(sottrai|togli|-)\s*(\d+)\s*ore?", request)
        if shift_match or "gmt" in request or "timezone" in request:
            amount = 1
            if shift_match and shift_match.group(2):
                amount = int(shift_match.group(2))
            if subtract_match:
                amount = -int(subtract_match.group(2))
            transformations.append({
                "type": "datetime_shift",
                "column_hint": "data sottoscrizione",
                "amount": amount,
                "unit": "hour",
                "reason": "source dates are GMT" if "gmt" in request else "requested datetime shift",
                "use_adjusted_column": "post aggiornamento" in request or "post aggiorn" in request,
            })

        wants_activation = any(term in request for term in [
            "tempo di attivazione",
            "tempi di attivazione",
            "data sottoscrizione",
            "creazione antenna",
        ])
        wants_concentration = any(term in request for term in [
            "giornate specifiche",
            "tempi lunghissimi",
            "concentrazione",
            "varianza",
            "anomali",
            "anomalie",
        ])
        return {
            "intent_type": "activation_time_temporal_concentration" if wants_activation and wants_concentration else "general_analysis",
            "requires_preprocessing": bool(transformations),
            "requested_transformations": transformations,
            "primary_question": (
                "Are long activation times concentrated on specific days or distributed variance?"
                if wants_concentration else ""
            ),
            "requested_metric": "activation_time" if wants_activation else None,
            "requires_temporal_concentration": wants_concentration,
            "requires_distribution_analysis": wants_activation,
        }


class TransformationPlanner:
    """Mappa trasformazioni richieste su colonne reali senza mutare gli originali."""

    def build_plan(self, intent: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
        transformations = []
        blocking_questions = []
        for item in intent.get("requested_transformations") or []:
            if item.get("type") != "datetime_shift":
                continue
            source = self._find_column(df, item.get("column_hint"))
            if not source:
                transformations.append({**item, "status": "requires_user_decision"})
                blocking_questions.append(
                    f"Quale colonna data devo usare per '{item.get('column_hint')}'?"
                )
                continue
            output = f"{source}_ADJUSTED"
            transformations.append({
                "type": "datetime_shift",
                "source_column": source,
                "output_column": output,
                "amount": item.get("amount", 1),
                "unit": item.get("unit", "hour"),
                "reason": item.get("reason", ""),
                "use_adjusted_column": item.get("use_adjusted_column", True),
                "status": "planned",
            })
        return {
            "transformations": transformations,
            "blocking_questions": blocking_questions,
        }

    def _find_column(self, df: pd.DataFrame, hint: str | None) -> str | None:
        if not isinstance(df, pd.DataFrame):
            return None
        normalized_hint = self._normalize(hint or "")
        preferred = ["datasottoscrizione", "data sottoscrizione", "sottoscrizione"]
        for column in df.columns:
            normalized = self._normalize(column)
            if normalized in {"datasottoscrizione", "datasottoscrizioneadjusted"}:
                return str(column)
            if normalized_hint and normalized_hint in normalized:
                return str(column)
            if any(term.replace(" ", "") in normalized for term in preferred):
                return str(column)
        return None

    def _normalize(self, value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())


class TransformationExecutor:
    """Esegue trasformazioni pianificate e produce metadata auditabili."""

    def execute(self, df: pd.DataFrame, transformation_plan: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
        transformed = df.copy()
        results = []
        applied = []
        transformed_columns = []
        for item in transformation_plan.get("transformations") or []:
            if item.get("type") != "datetime_shift" or item.get("status") != "planned":
                continue
            source = item["source_column"]
            output = item["output_column"]
            amount = item.get("amount", 1)
            unit = item.get("unit", "hour")
            logger.info(
                "Applying transformation datetime_shift %s -> %s %+s %s",
                source,
                output,
                amount,
                unit,
            )
            parsed = pd.to_datetime(transformed[source], errors="coerce")
            shifted = parsed + pd.to_timedelta(amount, unit=unit)
            transformed[output] = shifted
            result = {
                "type": "datetime_shift",
                "source_column": source,
                "output_column": output,
                "amount": amount,
                "unit": unit,
                "status": "applied",
                "parsed_count": int(parsed.notna().sum()),
                "missing_count": int(transformed[source].isna().sum()),
                "failed_parse_count": int(parsed.isna().sum() - transformed[source].isna().sum()),
                "min_before": str(parsed.min()) if parsed.notna().any() else None,
                "max_before": str(parsed.max()) if parsed.notna().any() else None,
                "min_after": str(shifted.min()) if shifted.notna().any() else None,
                "max_after": str(shifted.max()) if shifted.notna().any() else None,
            }
            results.append(result)
            applied.append(item)
            transformed_columns.append(output)
        return transformed, {
            "applied_transformations": applied,
            "transformation_results": results,
            "transformed_columns": transformed_columns,
        }


class DataQualityGate:
    """Applica gate qualità sul KPI principale e definisce policy sicure."""

    def evaluate_metric(self, df: pd.DataFrame, metric: str) -> dict[str, Any]:
        if not isinstance(df, pd.DataFrame) or metric not in df.columns:
            return {
                "status": "not_applicable",
                "quality_gate_results": [],
                "data_quality_issues": [],
                "metric_filtering_policy": {},
            }
        values = pd.to_numeric(df[metric], errors="coerce")
        total = int(len(values))
        missing_count = int(values.isna().sum())
        negative_count = int((values < 0).sum())
        negative_ratio = negative_count / total if total else 0.0
        missing_ratio = missing_count / total if total else 0.0
        severity = "high" if negative_ratio > 0.05 else "low"
        status = "requires_user_decision" if severity == "high" else "passed"
        issue = {
            "metric": metric,
            "status": status,
            "negative_duration_count": negative_count,
            "negative_duration_ratio": negative_ratio,
            "missing_count": missing_count,
            "missing_ratio": missing_ratio,
            "severity": severity,
            "message": "Sono presenti molte durate negative. Il KPI potrebbe essere distorto." if severity == "high" else "",
        }
        policy = {
            "metric": metric,
            "exclude_negative_from_primary_kpi": True,
            "negative_values_treatment": "data_quality_issue",
            "positive_filter": ">=0",
        }
        return {
            "status": status,
            "quality_gate_results": [issue],
            "data_quality_issues": [issue] if negative_count else [],
            "metric_filtering_policy": policy,
        }

    def apply_safe_policy(self, df: pd.DataFrame, gate_result: dict[str, Any]) -> pd.DataFrame:
        metric = (gate_result.get("metric_filtering_policy") or {}).get("metric")
        if metric not in df.columns:
            return df
        filtered = df.copy()
        values = pd.to_numeric(filtered[metric], errors="coerce")
        filtered.loc[values < 0, metric] = pd.NA
        return filtered


class AnalysisPlanBuilder:
    """Costruisce un piano analitico coerente con intent e quality policy."""

    def build(self, intent: dict[str, Any]) -> dict[str, Any]:
        if intent.get("intent_type") != "activation_time_temporal_concentration":
            return {"analysis_type": "general"}
        return {
            "analysis_type": "activation_time_temporal_concentration",
            "primary_metric": "TEMPO_ATTIVAZIONE_GIORNI",
            "kpi_filter": ">=0",
            "analyses": [
                "distribution_positive_durations",
                "percentiles_positive_durations",
                "temporal_concentration_positive_outliers",
                "daily_outlier_count",
                "daily_outlier_ratio",
                "variance_assessment",
                "data_quality_negative_durations",
            ],
            "segmentations": ["METODOCONSEGNA", "CANALETECNICO"],
            "exclusions": [
                "ID",
                "PYID",
                "CONTRATTOID",
                "SERIALNUMBER",
                "CODICEFISCALE",
                "negative_durations_from_primary_kpi",
            ],
        }


class VisualizationPlanner:
    """Produce una lista limitata di visualizzazioni richieste."""

    def build(self, intent: dict[str, Any], time_axis: str | None = None) -> list[dict[str, Any]]:
        if intent.get("intent_type") != "activation_time_temporal_concentration":
            return []
        metric = "TEMPO_ATTIVAZIONE_GIORNI"
        return [
            {
                "chart_type": "histogram",
                "metric": metric,
                "filter": ">=0",
                "title": "Distribuzione tempi di attivazione validi",
            },
            {
                "chart_type": "boxplot",
                "metric": metric,
                "filter": ">=0",
                "title": "Boxplot tempi di attivazione validi",
            },
            {
                "chart_type": "bar",
                "metric": metric,
                "filter": "positive_outliers",
                "title": "Concentrazione giornaliera outlier positivi",
            },
            {
                "chart_type": "scatter",
                "metric": metric,
                "x": time_axis or "DATASOTTOSCRIZIONE_ADJUSTED",
                "filter": ">=0",
                "title": "Data sottoscrizione adjusted vs tempo attivazione",
            },
        ]


class FollowupComparisonPlanner:
    """Calcola confronto baseline vs subset per follow-up filtrati."""

    def compare(self, baseline_df: pd.DataFrame, subset_df: pd.DataFrame, filter_spec: dict[str, Any], metric: str) -> dict[str, Any]:
        baseline = self._metric_summary(baseline_df, metric)
        subset = self._metric_summary(subset_df, metric)
        delta = {
            "median_pct": self._pct_delta(subset.get("median"), baseline.get("median")),
            "p95_pct": self._pct_delta(subset.get("p95"), baseline.get("p95")),
            "outlier_ratio_delta": self._num(subset.get("positive_outlier_ratio")) - self._num(baseline.get("positive_outlier_ratio")),
        }
        if delta["p95_pct"] is not None and delta["p95_pct"] > 10:
            conclusion = "subset_worse"
        elif delta["p95_pct"] is not None and delta["p95_pct"] < -10:
            conclusion = "subset_better"
        else:
            conclusion = "subset_similar"
        return {
            "baseline_rows": int(len(baseline_df)),
            "subset_rows": int(len(subset_df)),
            "filter": f"{filter_spec.get('column')} == {filter_spec.get('value')}",
            "metric": metric,
            "baseline": baseline,
            "subset": subset,
            "delta": delta,
            "conclusion": conclusion,
        }

    def _metric_summary(self, df: pd.DataFrame, metric: str) -> dict[str, Any]:
        if metric not in df.columns:
            return {"median": None, "p95": None, "positive_outlier_ratio": 0.0}
        values = pd.to_numeric(df[metric], errors="coerce")
        positive = values[values >= 0].dropna()
        if positive.empty:
            return {"median": None, "p95": None, "positive_outlier_ratio": 0.0}
        q1 = positive.quantile(0.25)
        q3 = positive.quantile(0.75)
        threshold = q3 + 1.5 * (q3 - q1)
        outliers = positive[positive > threshold]
        return {
            "median": float(positive.median()),
            "p95": float(positive.quantile(0.95)),
            "positive_outlier_ratio": float(len(outliers) / len(positive)),
        }

    def _pct_delta(self, value: Any, baseline: Any) -> float | None:
        if baseline in {None, 0} or value is None:
            return None
        return (float(value) - float(baseline)) / abs(float(baseline)) * 100

    def _num(self, value: Any) -> float:
        return float(value or 0)


class AnalyticalPlanningEngine:
    """Facade del planning deterministico richiesto prima dell'analisi."""

    def __init__(self):
        self.intent_parser = IntentParser()
        self.transformation_planner = TransformationPlanner()
        self.transformation_executor = TransformationExecutor()
        self.data_quality_gate = DataQualityGate()
        self.analysis_plan_builder = AnalysisPlanBuilder()
        self.visualization_planner = VisualizationPlanner()
        self.followup_comparison_planner = FollowupComparisonPlanner()

    def build_execution_plan(self, user_request: str, df: pd.DataFrame) -> dict[str, Any]:
        intent = self.intent_parser.parse(user_request)
        transformation_plan = self.transformation_planner.build_plan(intent, df)
        status = "ready"
        if transformation_plan["blocking_questions"]:
            status = "requires_user_decision"
        analysis_plan = self.analysis_plan_builder.build(intent)
        visualization_plan = self.visualization_planner.build(intent)
        return {
            "intent": intent,
            "transformations": transformation_plan["transformations"],
            "quality_gates": [],
            "feature_requirements": [
                {
                    "feature_name": "TEMPO_ATTIVAZIONE_GIORNI",
                    "use_adjusted_source": any(item.get("use_adjusted_column") for item in transformation_plan["transformations"]),
                }
            ] if intent.get("requested_metric") == "activation_time" else [],
            "analysis_plan": analysis_plan,
            "visualization_plan": visualization_plan,
            "followup_plan": {
                "mode": "compare_subset_vs_baseline" if intent.get("requested_metric") == "activation_time" else "standard",
                "metric": "TEMPO_ATTIVAZIONE_GIORNI" if intent.get("requested_metric") == "activation_time" else None,
            },
            "blocking_questions": transformation_plan["blocking_questions"],
            "warnings": [],
            "status": status,
        }
