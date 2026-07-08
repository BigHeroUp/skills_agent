"""Deterministic builders that derive reusable experience from the Knowledge Graph."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore

from .experience_models import AnalyticalExperience


class ExperienceBuilder:
    """Build deterministic analytical experience from existing analysis runs."""

    def __init__(
        self,
        query_engine: KnowledgeGraphQueryEngine | None = None,
        store: KnowledgeGraphStore | None = None,
        path: str | None = None,
    ) -> None:
        resolved_store = store or getattr(query_engine, "store", None) or KnowledgeGraphStore(path)
        self.store = resolved_store
        self.query_engine = query_engine or KnowledgeGraphQueryEngine(
            store=self.store,
            path=getattr(self.store, "path", path),
        )

    def build_from_latest_analyses(self, limit: int = 20) -> list[AnalyticalExperience]:
        runs = self.query_engine.get_latest_analysis_runs(limit=max(0, limit))
        return self.build_from_analysis_runs([run.get("id", "") for run in runs])

    def build_from_analysis_runs(self, run_ids: list[str]) -> list[AnalyticalExperience]:
        run_summaries = [summary for summary in self._collect_run_summaries(run_ids) if summary["run_id"]]
        experiences_by_id: dict[str, AnalyticalExperience] = {}

        for experience in self._build_metric_experiences(run_summaries):
            experiences_by_id[experience.id] = experience
        for experience in self._build_anomaly_experiences(run_summaries):
            experiences_by_id[experience.id] = experience
        for experience in self._build_root_cause_experiences(run_summaries):
            experiences_by_id[experience.id] = experience

        experiences = list(experiences_by_id.values())
        experiences.sort(key=lambda item: (item.id, item.title))
        return experiences

    def _collect_run_summaries(self, run_ids: list[str]) -> list[dict[str, Any]]:
        unique_run_ids: list[str] = []
        for run_id in run_ids or []:
            clean_run_id = str(run_id or "").strip()
            if clean_run_id and clean_run_id not in unique_run_ids:
                unique_run_ids.append(clean_run_id)

        summaries: list[dict[str, Any]] = []
        for run_id in unique_run_ids:
            lineage = self.query_engine.get_analysis_lineage(run_id)
            analysis_run = lineage.get("analysis_run") or {}
            properties = analysis_run.get("properties") or {}
            primary_metric = self._normalize(properties.get("primary_metric"))
            time_axis = self._normalize(properties.get("time_axis"))
            columns = sorted(
                {
                    self._normalize(column.get("label"))
                    for column in lineage.get("columns") or []
                    if self._normalize(column.get("label"))
                }
            )
            anomalies = sorted(
                {
                    self._normalize(
                        anomaly.get("label")
                        or (anomaly.get("properties") or {}).get("anomaly_type")
                    )
                    for anomaly in lineage.get("anomalies") or []
                    if self._normalize(
                        anomaly.get("label")
                        or (anomaly.get("properties") or {}).get("anomaly_type")
                    )
                }
            )
            root_causes = sorted(
                {
                    self._normalize(root_cause.get("label"))
                    for root_cause in lineage.get("root_causes") or []
                    if self._normalize(root_cause.get("label"))
                }
            )
            created_at = str(properties.get("created_at") or "")
            summaries.append(
                {
                    "run_id": run_id,
                    "primary_metric": primary_metric,
                    "time_axis": time_axis,
                    "columns": columns,
                    "anomalies": anomalies,
                    "root_causes": root_causes,
                    "created_at": created_at,
                }
            )
        return summaries

    def _build_metric_experiences(self, run_summaries: list[dict[str, Any]]) -> list[AnalyticalExperience]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for summary in run_summaries:
            if summary["primary_metric"]:
                grouped[summary["primary_metric"]].append(summary)

        experiences: list[AnalyticalExperience] = []
        for metric, items in grouped.items():
            if len(items) < 2:
                continue
            columns = sorted({column for item in items for column in item["columns"]})
            anomalies = sorted({anomaly for item in items for anomaly in item["anomalies"]})
            root_causes = sorted({cause for item in items for cause in item["root_causes"]})
            time_axis = next((item["time_axis"] for item in items if item["time_axis"]), "")
            recommended_steps = self._derive_recommended_steps(
                metric=metric,
                time_axis=time_axis,
                anomalies=anomalies,
                root_causes=root_causes,
                evidence_count=len(items),
            )
            timestamp = self._resolve_timestamp(items)
            experiences.append(
                AnalyticalExperience(
                    id=f"experience.metric.{self._slug(metric)}",
                    title=f"Esperienza riusabile sulla metrica {metric}",
                    description=(
                        f"La metrica {metric} compare in {len(items)} analysis_run e genera "
                        "un pattern analitico riutilizzabile."
                    ),
                    source_analysis_run_ids=[item["run_id"] for item in items],
                    metrics=[metric],
                    columns=columns,
                    anomalies=anomalies,
                    root_causes=root_causes,
                    recommended_steps=recommended_steps,
                    confidence=round(min(1.0, 0.45 + len(items) * 0.12), 2),
                    evidence_count=len(items),
                    created_at=timestamp,
                    updated_at=timestamp,
                    tags=sorted({"metric", metric, time_axis} - {""}),
                )
            )
        return experiences

    def _build_anomaly_experiences(self, run_summaries: list[dict[str, Any]]) -> list[AnalyticalExperience]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for summary in run_summaries:
            for anomaly in summary["anomalies"]:
                grouped[anomaly].append(summary)

        experiences: list[AnalyticalExperience] = []
        for anomaly, items in grouped.items():
            unique_runs = self._unique_run_summaries(items)
            if len(unique_runs) < 2:
                continue
            metrics = sorted({item["primary_metric"] for item in unique_runs if item["primary_metric"]})
            columns = sorted({column for item in unique_runs for column in item["columns"]})
            root_causes = sorted({cause for item in unique_runs for cause in item["root_causes"]})
            recommended_steps = self._derive_recommended_steps(
                metric=metrics[0] if metrics else "",
                time_axis=next((item["time_axis"] for item in unique_runs if item["time_axis"]), ""),
                anomalies=[anomaly],
                root_causes=root_causes,
                evidence_count=len(unique_runs),
            )
            timestamp = self._resolve_timestamp(unique_runs)
            experiences.append(
                AnalyticalExperience(
                    id=f"experience.anomaly.{self._slug(anomaly)}",
                    title=f"Pattern ricorrente di anomalia: {anomaly}",
                    description=(
                        f"L'anomalia {anomaly} ricorre in {len(unique_runs)} analysis_run e "
                        "può guidare verifiche riusabili."
                    ),
                    source_analysis_run_ids=[item["run_id"] for item in unique_runs],
                    metrics=metrics,
                    columns=columns,
                    anomalies=[anomaly],
                    root_causes=root_causes,
                    recommended_steps=recommended_steps,
                    confidence=round(min(1.0, 0.4 + len(unique_runs) * 0.15), 2),
                    evidence_count=len(unique_runs),
                    created_at=timestamp,
                    updated_at=timestamp,
                    tags=sorted({"anomaly", anomaly, "recurring"} - {""}),
                )
            )
        return experiences

    def _build_root_cause_experiences(self, run_summaries: list[dict[str, Any]]) -> list[AnalyticalExperience]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for summary in run_summaries:
            for cause in summary["root_causes"]:
                grouped[cause].append(summary)

        experiences: list[AnalyticalExperience] = []
        for root_cause, items in grouped.items():
            unique_runs = self._unique_run_summaries(items)
            if len(unique_runs) < 2:
                continue
            metrics = sorted({item["primary_metric"] for item in unique_runs if item["primary_metric"]})
            columns = sorted({column for item in unique_runs for column in item["columns"]})
            anomalies = sorted({anomaly for item in unique_runs for anomaly in item["anomalies"]})
            recommended_steps = self._derive_recommended_steps(
                metric=metrics[0] if metrics else "",
                time_axis=next((item["time_axis"] for item in unique_runs if item["time_axis"]), ""),
                anomalies=anomalies,
                root_causes=[root_cause],
                evidence_count=len(unique_runs),
            )
            timestamp = self._resolve_timestamp(unique_runs)
            experiences.append(
                AnalyticalExperience(
                    id=f"experience.root_cause.{self._slug(root_cause)}",
                    title=f"Root cause ricorrente: {root_cause}",
                    description=(
                        f"La root cause {root_cause} emerge in {len(unique_runs)} analysis_run "
                        "e rappresenta esperienza riutilizzabile."
                    ),
                    source_analysis_run_ids=[item["run_id"] for item in unique_runs],
                    metrics=metrics,
                    columns=columns,
                    anomalies=anomalies,
                    root_causes=[root_cause],
                    recommended_steps=recommended_steps,
                    confidence=round(min(1.0, 0.42 + len(unique_runs) * 0.15), 2),
                    evidence_count=len(unique_runs),
                    created_at=timestamp,
                    updated_at=timestamp,
                    tags=sorted({"root-cause", "recurring", self._classify_root_cause(root_cause)} - {""}),
                )
            )
        return experiences

    def _derive_recommended_steps(
        self,
        metric: str,
        time_axis: str,
        anomalies: list[str],
        root_causes: list[str],
        evidence_count: int,
    ) -> list[str]:
        steps: list[str] = []
        if metric and time_axis:
            steps.extend(
                [
                    f"Analizzare il trend temporale di {metric} su {time_axis}",
                    f"Calcolare percentili e distribuzione di {metric}",
                ]
            )
        elif metric:
            steps.append(f"Calcolare percentili e distribuzione di {metric}")
        if anomalies:
            steps.extend(
                [
                    "Eseguire un controllo outlier sulla metrica primaria",
                    "Applicare una segmentazione per isolare i cluster anomali",
                ]
            )
        if any(self._classify_root_cause(cause) == "infrastructure" for cause in root_causes):
            steps.append("Eseguire una verifica infrastrutturale mirata")
        if evidence_count >= 2 and not steps:
            steps.append("Confrontare distribuzione, segmentazione e segnali ricorrenti emersi nelle analisi")
        return self._dedupe(steps)

    def _resolve_timestamp(self, items: list[dict[str, Any]]) -> str:
        timestamps = sorted(
            [str(item.get("created_at") or "") for item in items if str(item.get("created_at") or "")],
            reverse=True,
        )
        return timestamps[0] if timestamps else datetime.utcnow().isoformat()

    def _classify_root_cause(self, root_cause: str) -> str:
        lowered = str(root_cause or "").lower()
        if any(term in lowered for term in ("performance", "degradation", "degrad", "infrastr", "backlog", "capacity", "laten")):
            return "infrastructure"
        return "general"

    def _unique_run_summaries(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            deduped[item["run_id"]] = item
        return [deduped[key] for key in sorted(deduped)]

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            clean_value = str(value or "").strip()
            if clean_value and clean_value not in result:
                result.append(clean_value)
        return result

    def _normalize(self, value: Any) -> str:
        return str(value or "").strip()

    def _slug(self, value: str) -> str:
        return (
            str(value or "")
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )
