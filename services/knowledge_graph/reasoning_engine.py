"""Reasoning deterministico basato su Knowledge Graph locale."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.consumption import ConsumerGovernanceMode
from services.knowledge_graph.governance import GOVERNANCE_POLICY_V1, GovernancePolicy
from services.knowledge_graph.store import KnowledgeGraphStore
from utils.context import AgentContext


STOPWORDS = {
    "a",
    "ad",
    "agli",
    "ai",
    "al",
    "alla",
    "alle",
    "analisi",
    "analizza",
    "analysis",
    "anche",
    "che",
    "col",
    "come",
    "con",
    "da",
    "dato",
    "dati",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "ed",
    "e",
    "gli",
    "ha",
    "hanno",
    "i",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "metric",
    "nel",
    "nella",
    "nelle",
    "non",
    "o",
    "per",
    "piu",
    "quale",
    "quali",
    "su",
    "the",
    "this",
    "tra",
    "un",
    "una",
}

HIGH_PRIORITY = "high"
MEDIUM_PRIORITY = "medium"
LOW_PRIORITY = "low"
DEFAULT_EXECUTION_TYPE = "deterministic_knowledge_reasoning"
STRATEGY_INSIGHT_LABELS = {
    "operational_recommendations",
    "trend_analysis",
    "anomaly_analysis",
    "segmentation_analysis",
    "knowledge_analysis_steps",
}
REPORT_INSIGHT_LABELS = {
    "analysis_report",
    "local_final_report",
}
ROOT_CAUSE_KEYWORDS = {
    "infrastruttur",
    "degrad",
    "performance",
    "satur",
    "backlog",
    "capacity",
    "laten",
    "sla",
}


def build_dataset_profile_from_context(context: AgentContext) -> dict[str, Any]:
    """Costruisce un profilo dataset sintetico senza persistere dati grezzi."""
    raw_data = context.raw_data if isinstance(context.raw_data, dict) else {}
    metadata = context.metadata if isinstance(context.metadata, dict) else {}
    dataframe = raw_data.get("dataframe")

    column_names = [str(column) for column in getattr(dataframe, "columns", [])]
    dtypes = (
        {str(column): str(dtype) for column, dtype in getattr(dataframe, "dtypes", {}).items()}
        if hasattr(getattr(dataframe, "dtypes", None), "items")
        else {}
    )
    shape = getattr(dataframe, "shape", None)
    row_count = int(shape[0]) if shape else 0
    column_count = int(shape[1]) if shape else len(column_names)
    semantic_roles = _normalize_semantic_roles(context.semantic_columns, column_names)
    source_type = metadata.get("source_type") or raw_data.get("source") or "unknown"

    keyword_sources = [
        str(context.user_input or ""),
        str(context.primary_metric or ""),
        str(context.time_axis or ""),
        str(source_type or ""),
    ]
    keyword_sources.extend(column_names[:12])

    profile = {
        "column_names": column_names[:250],
        "dtypes": dtypes,
        "row_count": row_count,
        "column_count": column_count,
        "primary_metric": context.primary_metric,
        "time_axis": context.time_axis,
        "source_type": source_type,
        "semantic_roles": semantic_roles,
        "detected_keywords": sorted(_extract_keywords(keyword_sources))[:50],
        "numeric_columns": _infer_columns_by_dtype(dtypes, include_numeric=True),
        "categorical_columns": _infer_columns_by_dtype(dtypes, include_numeric=False),
    }
    return profile


class KnowledgeReasoningEngine:
    """Motore deterministico che riusa memoria analitica dal Knowledge Graph."""

    def __init__(
        self,
        query_engine: KnowledgeGraphQueryEngine | None = None,
        store: KnowledgeGraphStore | None = None,
        path: str | None = None,
        governance_mode: ConsumerGovernanceMode | str = ConsumerGovernanceMode.LEGACY,
        governance_policy: GovernancePolicy = GOVERNANCE_POLICY_V1,
    ):
        resolved_store = store or getattr(query_engine, "store", None) or KnowledgeGraphStore(path)
        self.store = resolved_store
        self.query_engine = query_engine or KnowledgeGraphQueryEngine(
            store=self.store,
            path=getattr(self.store, "path", path),
            governance_mode=governance_mode,
            governance_policy=governance_policy,
        )
        self.snapshot = self.query_engine.snapshot

    def find_similar_analysis_runs(
        self,
        current_profile: dict,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Trova run analitiche simili usando scoring deterministico e spiegabile."""
        normalized_current = self._normalize_profile(current_profile)
        runs = [
            node.to_dict()
            for node in self.snapshot.nodes
            if getattr(node, "type", None) == "analysis_run"
        ]
        scored_runs: list[dict[str, Any]] = []
        for run in runs:
            run_id = str(run.get("id") or "")
            lineage = self.query_engine.get_analysis_lineage(run_id)
            candidate = self._build_profile_from_lineage(lineage)
            score, reasons = self._score_profiles(normalized_current, candidate)
            if score <= 0:
                continue
            if not reasons:
                reasons = ["profilo compatibile con la memoria analitica disponibile"]
            scored_runs.append(
                {
                    "run_id": run_id,
                    "label": run.get("label") or run_id,
                    "score": round(_clamp(score), 4),
                    "reasons": reasons,
                }
            )

        scored_runs.sort(
            key=lambda item: (
                float(item.get("score", 0.0)),
                str(self._created_at_for_run(item.get("run_id"))),
                str(item.get("run_id")),
            ),
            reverse=True,
        )
        return {
            "execution_type": DEFAULT_EXECUTION_TYPE,
            "similar_runs": scored_runs[: max(0, limit)],
        }

    def extract_reusable_patterns(self, analysis_run_ids: list[str]) -> dict[str, Any]:
        """Estrae pattern riutilizzabili da run analitiche gia archiviate."""
        unique_run_ids = []
        for run_id in analysis_run_ids or []:
            clean_run_id = str(run_id or "").strip()
            if clean_run_id and clean_run_id not in unique_run_ids:
                unique_run_ids.append(clean_run_id)

        counters = {
            "metrics": Counter(),
            "columns": Counter(),
            "anomalies": Counter(),
            "root_causes": Counter(),
            "strategies": Counter(),
            "reports": Counter(),
        }
        threshold = 1 if len(unique_run_ids) <= 1 else 2

        for run_id in unique_run_ids:
            lineage = self.query_engine.get_analysis_lineage(run_id)
            analysis_run = lineage.get("analysis_run") or {}
            run_properties = analysis_run.get("properties") or {}

            primary_metric = _normalize_scalar(run_properties.get("primary_metric"))
            if primary_metric:
                counters["metrics"][primary_metric] += 1

            for column in lineage.get("columns") or []:
                label = _normalize_scalar(column.get("label"))
                if label:
                    counters["columns"][label] += 1
                properties = column.get("properties") or {}
                if properties.get("is_primary_metric"):
                    metric_name = _normalize_scalar(properties.get("name") or column.get("label"))
                    if metric_name:
                        counters["metrics"][metric_name] += 1

            for anomaly in lineage.get("anomalies") or []:
                anomaly_name = _normalize_scalar(
                    anomaly.get("label")
                    or (anomaly.get("properties") or {}).get("anomaly_type")
                )
                if anomaly_name:
                    counters["anomalies"][anomaly_name] += 1

            for root_cause in lineage.get("root_causes") or []:
                cause_name = _normalize_scalar(root_cause.get("label"))
                if cause_name:
                    counters["root_causes"][cause_name] += 1
                for metric_name in (root_cause.get("properties") or {}).get("affected_metrics", []) or []:
                    clean_metric = _normalize_scalar(metric_name)
                    if clean_metric:
                        counters["metrics"][clean_metric] += 1

            for insight in lineage.get("insights") or []:
                label = _normalize_scalar(insight.get("label"))
                summary = (insight.get("properties") or {}).get("summary")
                if label in STRATEGY_INSIGHT_LABELS:
                    for strategy in self._extract_summary_strings(summary):
                        counters["strategies"][strategy] += 1
                    if not self._extract_summary_strings(summary):
                        counters["strategies"][label] += 1
                if label in REPORT_INSIGHT_LABELS:
                    counters["reports"][label] += 1

            for report in lineage.get("reports") or []:
                report_label = _normalize_scalar(report.get("label"))
                if report_label:
                    counters["reports"][report_label] += 1

        reusable_patterns = {
            key: self._select_recurring_values(counter, threshold)
            for key, counter in counters.items()
        }

        populated_categories = sum(1 for values in reusable_patterns.values() if values)
        support_ratio = min(1.0, len(unique_run_ids) / 5.0)
        coverage_ratio = populated_categories / len(reusable_patterns) if reusable_patterns else 0.0
        confidence = round(_clamp(0.45 * support_ratio + 0.55 * coverage_ratio), 4)
        return {
            "reusable_patterns": reusable_patterns,
            "confidence": confidence,
        }

    def recommend_next_analytical_steps(
        self,
        current_profile: dict,
        similar_runs: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Propone prossimi step analitici basati su profilo corrente e memoria storica."""
        normalized_current = self._normalize_profile(current_profile)
        similar_payload = similar_runs
        if similar_payload is None:
            similar_payload = self.find_similar_analysis_runs(normalized_current, limit=3).get(
                "similar_runs",
                [],
            )

        reusable_patterns = self.extract_reusable_patterns(
            [item.get("run_id") for item in similar_payload if isinstance(item, dict)]
        )
        pattern_values = reusable_patterns.get("reusable_patterns", {})
        recommendations: list[dict[str, Any]] = []
        seen_steps: set[str] = set()

        def add_step(step: str, reason: str, priority: str, source: str) -> None:
            clean_step = step.strip()
            if not clean_step or clean_step in seen_steps:
                return
            seen_steps.add(clean_step)
            recommendations.append(
                {
                    "step": clean_step,
                    "reason": reason.strip(),
                    "priority": priority,
                    "source": source,
                }
            )

        primary_metric = normalized_current.get("primary_metric")
        time_axis = normalized_current.get("time_axis")
        numeric_columns = normalized_current.get("numeric_columns") or []
        categorical_columns = normalized_current.get("categorical_columns") or []
        anomalies = pattern_values.get("anomalies") or []
        root_causes = pattern_values.get("root_causes") or []

        if primary_metric:
            add_step(
                f"Analizzare la distribuzione della metrica primaria {primary_metric}",
                f"La metrica {primary_metric} e il KPI principale del profilo corrente.",
                HIGH_PRIORITY,
                "current_profile",
            )
            add_step(
                f"Calcolare percentile P75/P90/P95/P99 per {primary_metric}",
                "I percentili aiutano a leggere code distributive e degradazioni operative.",
                HIGH_PRIORITY,
                "current_profile",
            )

        if time_axis:
            add_step(
                f"Analizzare il trend temporale rispetto a {time_axis}",
                f"La presenza di {time_axis} consente di leggere pattern nel tempo.",
                HIGH_PRIORITY,
                "current_profile",
            )
            add_step(
                f"Verificare la concentrazione temporale di picchi e anomalie su {time_axis}",
                "La dimensione temporale permette di distinguere eventi puntuali da fenomeni diffusi.",
                MEDIUM_PRIORITY,
                "current_profile",
            )

        if primary_metric and numeric_columns:
            add_step(
                f"Verificare outlier e deviazioni estreme su {primary_metric}",
                "Le metriche numeriche richiedono un controllo esplicito delle code e dei valori anomali.",
                HIGH_PRIORITY,
                "current_profile",
            )

        if len(numeric_columns) >= 2:
            add_step(
                "Verificare correlazioni tra le principali colonne numeriche",
                "La presenza di piu misure numeriche puo evidenziare driver comuni o dipendenze.",
                MEDIUM_PRIORITY,
                "current_profile",
            )

        preferred_segments = self._preferred_segmentation_columns(categorical_columns)
        for column_name in preferred_segments[:2]:
            metric_scope = primary_metric or "la metrica target"
            add_step(
                f"Segmentare {metric_scope} per {column_name}",
                f"La colonna categorica {column_name} e una candidata utile per spiegare variazioni e cluster.",
                HIGH_PRIORITY if column_name in {"stato", "status", "canale", "channel"} else MEDIUM_PRIORITY,
                "current_profile",
            )

        if similar_payload:
            add_step(
                "Confrontare i risultati correnti con analisi simili gia archiviate",
                "Le run storiche simili possono confermare pattern stabili o regressioni nuove.",
                MEDIUM_PRIORITY,
                "similar_runs",
            )

        if anomalies:
            anomaly_label = anomalies[0]
            add_step(
                f"Verificare se il dataset corrente mostra segnali analoghi a {anomaly_label}",
                f"Nelle analisi simili ricorre l'anomalia {anomaly_label}.",
                HIGH_PRIORITY,
                "reusable_patterns",
            )

        if root_causes:
            top_root_cause = root_causes[0]
            if any(keyword in top_root_cause for keyword in ROOT_CAUSE_KEYWORDS):
                add_step(
                    "Verificare una possibile root cause infrastrutturale o di performance degradation",
                    f"Le analisi simili collegano anomalie ricorrenti a {top_root_cause}.",
                    HIGH_PRIORITY,
                    "reusable_patterns",
                )
            else:
                add_step(
                    f"Validare la root cause ricorrente: {top_root_cause}",
                    "Le cause radice gia osservate possono accelerare la diagnosi del caso corrente.",
                    MEDIUM_PRIORITY,
                    "reusable_patterns",
                )

        if (pattern_values.get("columns") or []) and preferred_segments:
            add_step(
                "Confrontare le segmentazioni ricorrenti con quelle gia usate in analisi passate",
                "Le colonne piu frequenti nel Knowledge Graph possono suggerire breakdown gia efficaci.",
                LOW_PRIORITY,
                "reusable_patterns",
            )

        priority_order = {HIGH_PRIORITY: 0, MEDIUM_PRIORITY: 1, LOW_PRIORITY: 2}
        recommendations.sort(
            key=lambda item: (
                priority_order.get(item.get("priority"), 99),
                item.get("source", ""),
                item.get("step", ""),
            )
        )

        confidence_inputs = 0
        confidence_inputs += 1 if primary_metric else 0
        confidence_inputs += 1 if time_axis else 0
        confidence_inputs += 1 if numeric_columns else 0
        confidence_inputs += 1 if categorical_columns else 0
        confidence_inputs += 1 if similar_payload else 0
        confidence_inputs += 1 if anomalies or root_causes else 0
        confidence = round(_clamp(0.18 * confidence_inputs), 4)

        return {
            "recommended_steps": recommendations[:7],
            "confidence": confidence,
        }

    def build_reasoning_context_for_analysis(self, current_profile: dict) -> dict[str, Any]:
        """Orchestra similarita, pattern riutilizzabili e step raccomandati."""
        normalized_current = self._normalize_profile(current_profile)
        similarity = self.find_similar_analysis_runs(normalized_current)
        reusable_patterns = self.extract_reusable_patterns(
            [item.get("run_id") for item in similarity.get("similar_runs", [])]
        )
        recommendations = self.recommend_next_analytical_steps(
            normalized_current,
            similar_runs=similarity.get("similar_runs", []),
        )
        return {
            "execution_type": DEFAULT_EXECUTION_TYPE,
            "current_profile_summary": self._build_profile_summary(normalized_current),
            "similarity": similarity,
            "reusable_patterns": reusable_patterns,
            "recommendations": recommendations,
            "reasoning_summary": self._build_reasoning_summary(
                similarity,
                reusable_patterns,
                recommendations,
            ),
        }

    def _build_profile_from_lineage(self, lineage: dict[str, Any]) -> dict[str, Any]:
        analysis_run = lineage.get("analysis_run") or {}
        run_properties = analysis_run.get("properties") or {}
        dataset = (lineage.get("dataset") or [{}])[0]
        dataset_properties = dataset.get("properties") or {}
        columns = lineage.get("columns") or []

        column_names = [str(column.get("label") or "") for column in columns if column.get("label")]
        dtypes = {
            str(column.get("label")): str((column.get("properties") or {}).get("dtype"))
            for column in columns
            if column.get("label")
        }
        semantic_roles = {
            str(column.get("label")): str((column.get("properties") or {}).get("semantic_role"))
            for column in columns
            if (column.get("properties") or {}).get("semantic_role")
        }

        keyword_sources = [
            analysis_run.get("label") or "",
            run_properties.get("user_input") or "",
            run_properties.get("primary_metric") or "",
            run_properties.get("time_axis") or "",
        ]
        keyword_sources.extend(column_names)
        keyword_sources.extend(
            [
                anomaly.get("label") or ""
                for anomaly in lineage.get("anomalies") or []
            ]
        )
        keyword_sources.extend(
            [
                root_cause.get("label") or ""
                for root_cause in lineage.get("root_causes") or []
            ]
        )

        return self._normalize_profile(
            {
                "column_names": column_names,
                "dtypes": dtypes,
                "row_count": run_properties.get("row_count") or dataset_properties.get("row_count"),
                "column_count": run_properties.get("column_count") or dataset_properties.get("column_count"),
                "primary_metric": run_properties.get("primary_metric"),
                "time_axis": run_properties.get("time_axis"),
                "source_type": run_properties.get("source_type") or dataset_properties.get("source_type"),
                "semantic_roles": semantic_roles,
                "detected_keywords": sorted(_extract_keywords(keyword_sources)),
                "numeric_columns": _infer_columns_by_dtype(dtypes, include_numeric=True),
                "categorical_columns": _infer_columns_by_dtype(dtypes, include_numeric=False),
            }
        )

    def _score_profiles(self, current: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, list[str]]:
        weights = {
            "column_names": 0.26,
            "primary_metric": 0.20,
            "time_axis": 0.12,
            "source_type": 0.10,
            "semantic_roles": 0.14,
            "shape": 0.10,
            "keywords": 0.08,
        }
        current_columns = set(current.get("column_names") or [])
        candidate_columns = set(candidate.get("column_names") or [])
        column_overlap = _jaccard(current_columns, candidate_columns)
        primary_metric_score = _exact_match(current.get("primary_metric"), candidate.get("primary_metric"))
        time_axis_score = _exact_match(current.get("time_axis"), candidate.get("time_axis"))
        source_type_score = _exact_match(current.get("source_type"), candidate.get("source_type"))
        semantic_score = _jaccard(
            set((current.get("semantic_roles") or {}).values()),
            set((candidate.get("semantic_roles") or {}).values()),
        )
        shape_score = _shape_similarity(
            current.get("row_count"),
            current.get("column_count"),
            candidate.get("row_count"),
            candidate.get("column_count"),
        )
        keyword_score = _jaccard(
            set(current.get("detected_keywords") or []),
            set(candidate.get("detected_keywords") or []),
        )

        score = (
            column_overlap * weights["column_names"]
            + primary_metric_score * weights["primary_metric"]
            + time_axis_score * weights["time_axis"]
            + source_type_score * weights["source_type"]
            + semantic_score * weights["semantic_roles"]
            + shape_score * weights["shape"]
            + keyword_score * weights["keywords"]
        )

        reasons: list[str] = []
        if column_overlap > 0:
            overlap = sorted(current_columns.intersection(candidate_columns))
            reasons.append(f"overlap colonne: {', '.join(overlap[:4])}")
        if primary_metric_score:
            reasons.append(f"stessa metrica primaria: {candidate.get('primary_metric')}")
        if time_axis_score:
            reasons.append(f"stesso asse temporale: {candidate.get('time_axis')}")
        if source_type_score:
            reasons.append(f"stessa sorgente: {candidate.get('source_type')}")
        if semantic_score > 0:
            common_roles = sorted(
                set((current.get("semantic_roles") or {}).values()).intersection(
                    set((candidate.get("semantic_roles") or {}).values())
                )
            )
            reasons.append(f"ruoli semantici comuni: {', '.join(common_roles[:4])}")
        if shape_score >= 0.6:
            reasons.append("dimensioni dataset comparabili")
        if keyword_score > 0:
            common_keywords = sorted(
                set(current.get("detected_keywords") or []).intersection(
                    set(candidate.get("detected_keywords") or [])
                )
            )
            reasons.append(f"keyword comuni: {', '.join(common_keywords[:4])}")
        return _clamp(score), reasons

    def _normalize_profile(self, profile: dict[str, Any] | None) -> dict[str, Any]:
        payload = profile if isinstance(profile, dict) else {}
        column_names = [_normalize_scalar(item) for item in payload.get("column_names", [])]
        column_names = [item for item in column_names if item]
        dtypes = {
            _normalize_scalar(key): str(value)
            for key, value in (payload.get("dtypes") or {}).items()
            if _normalize_scalar(key)
        }
        semantic_roles = _normalize_semantic_roles(payload.get("semantic_roles"), column_names)
        return {
            "column_names": sorted(dict.fromkeys(column_names)),
            "dtypes": dtypes,
            "row_count": _to_int(payload.get("row_count")),
            "column_count": _to_int(payload.get("column_count")),
            "primary_metric": _normalize_scalar(payload.get("primary_metric")),
            "time_axis": _normalize_scalar(payload.get("time_axis")),
            "source_type": _normalize_scalar(payload.get("source_type")),
            "semantic_roles": semantic_roles,
            "detected_keywords": sorted(
                dict.fromkeys(
                    [
                        token
                        for token in (
                            _normalize_scalar(item)
                            for item in payload.get("detected_keywords", [])
                        )
                        if token
                    ]
                )
            )[:50],
            "numeric_columns": [
                _normalize_scalar(item)
                for item in (payload.get("numeric_columns") or _infer_columns_by_dtype(dtypes, include_numeric=True))
                if _normalize_scalar(item)
            ][:250],
            "categorical_columns": [
                _normalize_scalar(item)
                for item in (
                    payload.get("categorical_columns")
                    or _infer_columns_by_dtype(dtypes, include_numeric=False)
                )
                if _normalize_scalar(item)
            ][:250],
        }

    def _build_profile_summary(self, profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "row_count": profile.get("row_count"),
            "column_count": profile.get("column_count"),
            "primary_metric": profile.get("primary_metric"),
            "time_axis": profile.get("time_axis"),
            "source_type": profile.get("source_type"),
            "column_names": (profile.get("column_names") or [])[:12],
            "semantic_roles": profile.get("semantic_roles") or {},
            "detected_keywords": (profile.get("detected_keywords") or [])[:12],
        }

    def _build_reasoning_summary(
        self,
        similarity: dict[str, Any],
        reusable_patterns: dict[str, Any],
        recommendations: dict[str, Any],
    ) -> str:
        similar_runs = similarity.get("similar_runs") or []
        patterns = reusable_patterns.get("reusable_patterns") or {}
        top_steps = recommendations.get("recommended_steps") or []

        top_run = similar_runs[0] if similar_runs else None
        if top_run:
            first_sentence = (
                f"Sono state trovate {len(similar_runs)} analisi simili; la piu rilevante e "
                f"'{top_run.get('label')}' con score {top_run.get('score'):.2f}."
            )
        else:
            first_sentence = "Non sono state trovate analisi storiche sufficientemente simili nel Knowledge Graph."

        recurring_metrics = patterns.get("metrics") or []
        recurring_anomalies = patterns.get("anomalies") or []
        top_step = top_steps[0]["step"] if top_steps else "nessuno step prioritario disponibile"
        second_sentence = (
            f"I pattern piu ricorrenti riguardano metriche {', '.join(recurring_metrics[:3]) or 'non disponibili'} "
            f"e anomalie {', '.join(recurring_anomalies[:3]) or 'non disponibili'}."
        )
        third_sentence = f"Il prossimo step consigliato e: {top_step}."
        return " ".join([first_sentence, second_sentence, third_sentence])

    def _extract_summary_strings(self, summary: Any) -> list[str]:
        if isinstance(summary, str):
            return [_normalize_scalar(summary)] if _normalize_scalar(summary) else []
        if isinstance(summary, list):
            return [
                normalized
                for item in summary
                if (normalized := _normalize_scalar(item))
            ]
        if isinstance(summary, dict):
            return [
                normalized
                for value in summary.values()
                if (normalized := _normalize_scalar(value))
            ]
        return []

    def _select_recurring_values(self, counter: Counter, threshold: int) -> list[str]:
        selected = [
            value
            for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            if value and count >= threshold
        ]
        return selected[:8]

    def _preferred_segmentation_columns(self, categorical_columns: list[str]) -> list[str]:
        priority_terms = ("stato", "status", "canale", "channel", "tipologia", "categoria", "type")
        ordered = []
        for column_name in categorical_columns:
            if any(term in column_name for term in priority_terms):
                ordered.append(column_name)
        for column_name in categorical_columns:
            if column_name not in ordered:
                ordered.append(column_name)
        return ordered

    def _created_at_for_run(self, run_id: str | None) -> str:
        if not run_id:
            return ""
        lineage = self.query_engine.get_analysis_lineage(run_id)
        analysis_run = lineage.get("analysis_run") or {}
        return str((analysis_run.get("properties") or {}).get("created_at") or "")


def _normalize_semantic_roles(raw_roles: Any, column_names: list[str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if not isinstance(raw_roles, dict):
        return normalized

    for column_name in column_names:
        role = _extract_semantic_role(raw_roles, column_name)
        if role:
            normalized[_normalize_scalar(column_name)] = _normalize_scalar(role)

    for key, value in raw_roles.items():
        normalized_key = _normalize_scalar(key)
        if normalized_key in normalized:
            continue
        if isinstance(value, str) and normalized_key:
            normalized[normalized_key] = _normalize_scalar(value)
        elif isinstance(value, dict) and normalized_key:
            role = value.get("semantic_role") or value.get("role") or value.get("type")
            if role:
                normalized[normalized_key] = _normalize_scalar(role)
    return normalized


def _extract_semantic_role(raw_roles: dict[str, Any], column_name: str) -> str | None:
    direct = raw_roles.get(column_name)
    if isinstance(direct, str):
        return direct
    if isinstance(direct, dict):
        return direct.get("semantic_role") or direct.get("role") or direct.get("type")
    for role_name, payload in raw_roles.items():
        if isinstance(payload, list) and column_name in payload:
            return str(role_name)
        if isinstance(payload, dict):
            columns = payload.get("columns") or payload.get("matches") or []
            if isinstance(columns, list) and column_name in columns:
                return str(role_name)
    return None


def _infer_columns_by_dtype(dtypes: dict[str, str], include_numeric: bool) -> list[str]:
    numeric_markers = ("int", "float", "double", "decimal", "number")
    selected = []
    for column_name, dtype in dtypes.items():
        dtype_name = str(dtype).lower()
        is_numeric = any(marker in dtype_name for marker in numeric_markers)
        if include_numeric and is_numeric:
            selected.append(column_name)
        if not include_numeric and not is_numeric:
            selected.append(column_name)
    return selected


def _extract_keywords(sources: list[str]) -> set[str]:
    tokens: set[str] = set()
    for source in sources:
        for token in re.findall(r"[a-zA-Z0-9_]{3,}", str(source or "").lower()):
            if token not in STOPWORDS:
                tokens.add(token)
    return tokens


def _normalize_scalar(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _exact_match(left: str | None, right: str | None) -> float:
    return 1.0 if left and right and left == right else 0.0


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left.union(right)
    if not union:
        return 0.0
    return len(left.intersection(right)) / len(union)


def _shape_similarity(
    current_rows: int | None,
    current_columns: int | None,
    candidate_rows: int | None,
    candidate_columns: int | None,
) -> float:
    row_score = _single_dimension_similarity(current_rows, candidate_rows, logarithmic=True)
    column_score = _single_dimension_similarity(current_columns, candidate_columns, logarithmic=False)
    available = [score for score in [row_score, column_score] if score is not None]
    if not available:
        return 0.0
    return sum(available) / len(available)


def _single_dimension_similarity(
    current_value: int | None,
    candidate_value: int | None,
    logarithmic: bool,
) -> float | None:
    if current_value is None or candidate_value is None or current_value < 0 or candidate_value < 0:
        return None
    if current_value == candidate_value:
        return 1.0
    if logarithmic:
        distance = abs(math.log1p(current_value) - math.log1p(candidate_value))
        return _clamp(1.0 - min(distance / 6.0, 1.0))
    baseline = max(current_value, candidate_value, 1)
    return _clamp(1.0 - (abs(current_value - candidate_value) / baseline))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))
