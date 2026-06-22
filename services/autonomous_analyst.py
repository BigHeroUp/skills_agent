"""Planner deterministico multi-step per analisi autonome."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from services.analysis_engine import AnalysisEngine, AnalysisPlan
from utils.data_analysis import summarize_dataframe


@dataclass
class AutonomousAnalysisStep:
    step_id: str
    title: str
    analysis_plan: AnalysisPlan
    reason: str
    priority: int
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["analysis_plan"] = self.analysis_plan.to_dict()
        return payload


@dataclass
class AutonomousAnalysisPlan:
    objective: str
    steps: list[AutonomousAnalysisStep]
    dataset_profile: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "steps": [step.to_dict() for step in self.steps],
            "dataset_profile": self.dataset_profile,
        }


@dataclass
class AutonomousAnalysisResult:
    step_id: str
    title: str
    status: str
    result: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousAnalyst:
    """Costruisce ed esegue un piano autonomo senza chiamate LLM."""

    BROAD_REQUEST_TERMS = [
        "analizza il dataset",
        "analizza i dati",
        "analizza i ticket",
        "analisi completa",
        "fammi un'analisi completa",
        "trova anomalie",
        "dimmi cosa vedi",
        "cosa vedi nei dati",
        "fai una panoramica",
        "panoramica",
        "overview",
    ]

    def __init__(self, analysis_engine: AnalysisEngine | None = None):
        self.analysis_engine = analysis_engine or AnalysisEngine()

    def should_run_autonomous(self, user_request: str) -> bool:
        request = (user_request or "").lower()
        return any(term in request for term in self.BROAD_REQUEST_TERMS)

    def run(self, user_request: str, df: pd.DataFrame) -> dict[str, Any]:
        """Pianifica, esegue e sintetizza una analisi multi-step."""
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {
                "autonomous_analysis_plan": AutonomousAnalysisPlan(
                    objective=user_request,
                    steps=[],
                    dataset_profile={"status": "empty"},
                ).to_dict(),
                "autonomous_analysis_results": [],
                "autonomous_executive_summary": "Nessun dataframe disponibile per l'analisi autonoma.",
                "autonomous_recommendations": ["Caricare un dataset valido prima di richiedere una panoramica."],
            }

        plan = self.build_plan(user_request, df)
        results = self.execute_plan(plan, df)
        return {
            "autonomous_analysis_plan": plan.to_dict(),
            "autonomous_analysis_results": [result.to_dict() for result in results],
            "autonomous_executive_summary": self.build_executive_summary(plan, results),
            "autonomous_recommendations": self.build_recommendations(plan, results),
        }

    def build_plan(self, user_request: str, df: pd.DataFrame) -> AutonomousAnalysisPlan:
        summary = summarize_dataframe(df)
        steps: list[AutonomousAnalysisStep] = []

        categorical_columns = summary.get("categorical_columns", [])
        numeric_columns = summary.get("numeric_columns", [])
        datetime_columns = summary.get("datetime_columns", [])

        status_column = self._find_status_column(df) or (categorical_columns[0] if categorical_columns else None)
        if status_column:
            steps.append(AutonomousAnalysisStep(
                step_id="category-distribution",
                title=f"Distribuzione per {status_column}",
                analysis_plan=AnalysisPlan(
                    analysis_type="count_occurrences",
                    target_column=status_column,
                    limit=20,
                    description=f"Conteggio occorrenze per {status_column}.",
                ),
                reason="Capire la distribuzione principale del dataset.",
                priority=10,
            ))

        time_column = self._find_datetime_column(df) or (datetime_columns[0] if datetime_columns else None)
        if time_column:
            steps.append(AutonomousAnalysisStep(
                step_id="time-trend",
                title=f"Trend temporale su {time_column}",
                analysis_plan=AnalysisPlan(
                    analysis_type="time_trend",
                    time_column=time_column,
                    value_column=numeric_columns[0] if numeric_columns else None,
                    aggregation="sum" if numeric_columns else "count",
                    limit=50,
                    description=f"Andamento temporale calcolato su {time_column}.",
                ),
                reason="Verificare andamento e stagionalita nel tempo.",
                priority=20,
            ))

        start_col, end_col = self._find_start_end_datetime_columns(df)
        if start_col and end_col:
            steps.append(AutonomousAnalysisStep(
                step_id="duration-summary",
                title=f"Tempo medio tra {start_col} e {end_col}",
                analysis_plan=AnalysisPlan(
                    analysis_type="duration_between_dates",
                    time_column=start_col,
                    target_column=end_col,
                    description=f"Durata tra {start_col} e {end_col}.",
                ),
                reason="Stimare tempi medi di attraversamento/risoluzione.",
                priority=25,
            ))

        if categorical_columns:
            for index, column in enumerate(categorical_columns[:2]):
                if column == status_column:
                    continue
                steps.append(AutonomousAnalysisStep(
                    step_id=f"top-category-{index + 1}",
                    title=f"Top valori per {column}",
                    analysis_plan=AnalysisPlan(
                        analysis_type="top_n",
                        target_column=column,
                        value_column=numeric_columns[0] if numeric_columns else None,
                        aggregation="sum" if numeric_columns else "count",
                        limit=10,
                        description=f"Top valori per {column}.",
                    ),
                    reason="Identificare categorie dominanti o concentrazioni.",
                    priority=30 + index,
                ))

        if numeric_columns:
            steps.append(AutonomousAnalysisStep(
                step_id="numeric-summary",
                title=f"Aggregazioni numeriche su {numeric_columns[0]}",
                analysis_plan=AnalysisPlan(
                    analysis_type="numeric_aggregation",
                    group_by_column=status_column,
                    value_column=numeric_columns[0],
                    aggregation="mean",
                    limit=20,
                    description=f"Media di {numeric_columns[0]}" + (f" per {status_column}." if status_column else "."),
                ),
                reason="Calcolare metriche numeriche principali.",
                priority=40,
            ))

        steps.append(AutonomousAnalysisStep(
            step_id="null-detection",
            title="Rilevazione valori nulli",
            analysis_plan=AnalysisPlan(
                analysis_type="null_detection",
                limit=20,
                description="Controllo qualita su valori nulli.",
            ),
            reason="Valutare completezza e qualita dati.",
            priority=90,
        ))
        steps.append(AutonomousAnalysisStep(
            step_id="duplicate-detection",
            title="Rilevazione duplicati",
            analysis_plan=AnalysisPlan(
                analysis_type="duplicate_detection",
                limit=10,
                description="Controllo qualita su righe duplicate.",
            ),
            reason="Individuare duplicati che possono alterare i risultati.",
            priority=95,
        ))

        steps.sort(key=lambda step: step.priority)
        return AutonomousAnalysisPlan(
            objective=user_request,
            steps=steps,
            dataset_profile={
                "row_count": summary.get("row_count", int(len(df))),
                "column_count": summary.get("column_count", int(len(df.columns))),
                "columns": summary.get("columns", [str(column) for column in df.columns]),
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "datetime_columns": datetime_columns,
            },
        )

    def execute_plan(self, plan: AutonomousAnalysisPlan, df: pd.DataFrame) -> list[AutonomousAnalysisResult]:
        results: list[AutonomousAnalysisResult] = []
        for step in plan.steps:
            try:
                if step.analysis_plan.analysis_type == "duration_between_dates":
                    result = self._duration_between_dates(df, step.analysis_plan)
                else:
                    result = self.analysis_engine.execute_plan(df, step.analysis_plan)
                step.status = "completed"
                results.append(AutonomousAnalysisResult(
                    step_id=step.step_id,
                    title=step.title,
                    status="completed",
                    result=result,
                ))
            except Exception as exc:
                step.status = "error"
                results.append(AutonomousAnalysisResult(
                    step_id=step.step_id,
                    title=step.title,
                    status="error",
                    result={},
                    error=str(exc),
                ))
        return results

    def build_executive_summary(
        self,
        plan: AutonomousAnalysisPlan,
        results: list[AutonomousAnalysisResult],
    ) -> str:
        completed = [result for result in results if result.status == "completed"]
        errors = [result for result in results if result.status != "completed"]
        profile = plan.dataset_profile
        return (
            f"Analisi autonoma completata su {profile.get('row_count', 0)} righe e "
            f"{profile.get('column_count', 0)} colonne. "
            f"Step completati: {len(completed)}/{len(results)}. "
            f"Step con errore: {len(errors)}."
        )

    def build_recommendations(
        self,
        plan: AutonomousAnalysisPlan,
        results: list[AutonomousAnalysisResult],
    ) -> list[str]:
        recommendations = []
        for result in results:
            if result.step_id == "null-detection":
                total_nulls = result.result.get("total_nulls", 0)
                if total_nulls:
                    recommendations.append(f"Gestire {total_nulls} valori nulli prima di decisioni operative.")
            if result.step_id == "duplicate-detection":
                duplicates = result.result.get("duplicate_rows", 0)
                if duplicates:
                    recommendations.append(f"Verificare {duplicates} righe duplicate rilevate.")
            if result.step_id == "time-trend" and not result.result.get("points"):
                recommendations.append("Validare la colonna temporale: non sono stati prodotti punti trend.")

        if not recommendations:
            recommendations.append("Dataset pronto per analisi successive; nessuna anomalia strutturale critica rilevata.")
        return recommendations

    def _duration_between_dates(self, df: pd.DataFrame, plan: AnalysisPlan) -> dict[str, Any]:
        start_col = plan.time_column
        end_col = plan.target_column
        if not start_col or not end_col or start_col not in df.columns or end_col not in df.columns:
            raise ValueError("Colonne data inizio/fine non disponibili.")

        start_dates = pd.to_datetime(df[start_col], errors="coerce")
        end_dates = pd.to_datetime(df[end_col], errors="coerce")
        durations = end_dates - start_dates
        valid = durations[(start_dates.notna()) & (end_dates.notna()) & (durations >= pd.Timedelta(0))]
        if valid.empty:
            return {
                "analysis_type": "duration_between_dates",
                "start_column": str(start_col),
                "end_column": str(end_col),
                "valid_rows": 0,
                "status": "empty",
            }

        return {
            "analysis_type": "duration_between_dates",
            "start_column": str(start_col),
            "end_column": str(end_col),
            "valid_rows": int(valid.count()),
            "average_hours": round(valid.mean().total_seconds() / 3600, 4),
            "median_hours": round(valid.median().total_seconds() / 3600, 4),
            "min_hours": round(valid.min().total_seconds() / 3600, 4),
            "max_hours": round(valid.max().total_seconds() / 3600, 4),
            "status": "computed",
        }

    def _find_status_column(self, df: pd.DataFrame) -> str | None:
        keywords = ["stato", "status", "state", "fase", "esito"]
        for column in df.columns:
            normalized = str(column).lower().replace("_", " ")
            if any(keyword in normalized for keyword in keywords):
                return str(column)
        return None

    def _find_datetime_column(self, df: pd.DataFrame) -> str | None:
        datetime_columns = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
        if datetime_columns:
            return str(datetime_columns[0])
        for column in df.columns:
            normalized = str(column).lower().replace("_", " ")
            if any(keyword in normalized for keyword in [
                "data",
                "date",
                "time",
                "timestamp",
                "created",
                "resolved",
                "updated",
                "closed",
                "opened",
            ]):
                parsed = pd.to_datetime(df[column], errors="coerce")
                if parsed.notna().sum() >= max(1, int(len(df) * 0.2)):
                    return str(column)
        return None

    def _find_start_end_datetime_columns(self, df: pd.DataFrame) -> tuple[str | None, str | None]:
        start_keywords = ["created", "creazione", "apertura", "start", "opened", "inizio"]
        end_keywords = ["resolved", "risoluzione", "chiusura", "closed", "updated", "fine", "end"]
        start_col = self._find_datetime_column_by_keywords(df, start_keywords)
        end_col = self._find_datetime_column_by_keywords(df, end_keywords)
        if start_col and end_col and start_col != end_col:
            return start_col, end_col
        return None, None

    def _find_datetime_column_by_keywords(self, df: pd.DataFrame, keywords: list[str]) -> str | None:
        for column in df.columns:
            normalized = str(column).lower().replace("_", " ")
            if any(keyword in normalized for keyword in keywords):
                parsed = pd.to_datetime(df[column], errors="coerce")
                if parsed.notna().sum() >= max(1, int(len(df) * 0.2)):
                    return str(column)
        return None
