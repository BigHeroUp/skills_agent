"""Knowledge Base locale dei pattern analitici ricorrenti."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from services.learning_engine import LearningEngine


class PatternKnowledgeEngine:
    """Rileva pattern e suggerisce best practice senza chiamate OpenAI."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        patterns: list[dict[str, Any]] | None = None,
        learning_engine: LearningEngine | None = None,
        learning_state: dict[str, Any] | None = None,
    ):
        catalog = patterns if patterns is not None else self._default_patterns()
        self._patterns = {
            pattern["pattern_id"]: copy.deepcopy(pattern)
            for pattern in catalog
        }
        self._learning_engine = learning_engine or (
            LearningEngine(learning_state) if learning_state else None
        )

    def detect_patterns(
        self,
        user_request: str,
        dataframe_metadata: dict | None = None,
    ) -> list[dict]:
        """Associa la richiesta ai pattern noti usando regole locali."""
        request = self._normalize(user_request)
        metadata = dataframe_metadata if isinstance(dataframe_metadata, dict) else {}
        detected = []

        for pattern in self._patterns.values():
            matched_keywords = [
                keyword
                for keyword in pattern["trigger_keywords"]
                if self._keyword_matches(request, keyword)
            ]
            metadata_score, metadata_signals = self._metadata_score(
                pattern["pattern_id"],
                metadata,
            )
            keyword_score = min(0.85, len(matched_keywords) * 0.22)
            confidence = min(
                0.99,
                pattern["confidence_score"] + keyword_score + metadata_score,
            )
            if not matched_keywords and metadata_score < 0.2:
                continue

            match = copy.deepcopy(pattern)
            match["confidence_score"] = round(confidence, 4)
            match["matched_keywords"] = matched_keywords
            match["metadata_signals"] = metadata_signals
            detected.append(match)

        detected = self.rank_patterns(user_request, detected)
        return detected

    def rank_patterns(
        self,
        user_request: str,
        patterns: list[dict],
        learning_state: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Ordina i pattern usando il Learning Engine quando disponibile."""
        learning_engine = self._learning_engine
        if learning_state is not None:
            learning_engine = LearningEngine(learning_state)
        if learning_engine is not None:
            return learning_engine.recommend_patterns(user_request, patterns)
        ranked = copy.deepcopy(patterns or [])
        ranked.sort(key=lambda item: (-item.get("confidence_score", 0), item["pattern_id"]))
        return ranked

    def suggest_analysis_steps(self, patterns: list[dict]) -> list[dict]:
        """Converte i pattern rilevati in una sequenza di analisi consigliate."""
        steps = []
        seen = set()
        for pattern in patterns or []:
            pattern_id = pattern.get("pattern_id")
            catalog_pattern = self._patterns.get(pattern_id, pattern)
            for index, step in enumerate(
                catalog_pattern.get("recommended_analysis_steps", []),
                start=1,
            ):
                step_key = (pattern_id, step.get("analysis_type"), step.get("metric"))
                if step_key in seen:
                    continue
                seen.add(step_key)
                steps.append({
                    "step_id": f"{pattern_id}-{index}",
                    "pattern_id": pattern_id,
                    "title": step["title"],
                    "analysis_type": step["analysis_type"],
                    "metric": step.get("metric"),
                    "grouping": step.get("grouping"),
                    "reason": step["reason"],
                    "priority": int(step.get("priority", 50)),
                    "confidence_score": pattern.get(
                        "confidence_score",
                        catalog_pattern.get("confidence_score", 0.0),
                    ),
                })
        steps.sort(key=lambda item: (item["priority"], item["step_id"]))
        return steps

    def enrich_analysis_plan(
        self,
        base_plan: dict,
        user_request: str,
        dataframe_metadata: dict | None = None,
    ) -> dict:
        """Aggiunge conoscenza analitica senza cambiare il calcolo eseguito."""
        plan = copy.deepcopy(base_plan) if isinstance(base_plan, dict) else {}
        patterns = self.detect_patterns(user_request, dataframe_metadata)
        steps = self.suggest_analysis_steps(patterns)
        notes = []
        metrics = []
        groupings = []
        charts = []

        for pattern in patterns:
            notes.extend(pattern.get("senior_analyst_notes", []))
            metrics.extend(pattern.get("recommended_metrics", []))
            groupings.extend(pattern.get("recommended_groupings", []))
            charts.extend(pattern.get("recommended_charts", []))

        plan["knowledge_enrichment"] = {
            "schema_version": self.SCHEMA_VERSION,
            "detected_pattern_ids": [
                pattern["pattern_id"] for pattern in patterns
            ],
            "patterns": patterns,
            "suggested_analysis_steps": steps,
            "recommended_metrics": self._unique(metrics),
            "recommended_groupings": self._unique(groupings),
            "recommended_charts": self._unique(charts),
            "senior_analyst_notes": self._unique(notes),
        }
        return self._json_safe(plan)

    def export_knowledge_base(self) -> dict:
        """Esporta il catalogo in un formato pronto per persistenza SQLite."""
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "storage": "memory",
            "pattern_count": len(self._patterns),
            "learning_state": (
                self._learning_engine.export_learning_state()
                if self._learning_engine is not None
                else None
            ),
            "patterns": [
                copy.deepcopy(self._patterns[pattern_id])
                for pattern_id in sorted(self._patterns)
            ],
        })

    def _metadata_score(
        self,
        pattern_id: str,
        metadata: dict[str, Any],
    ) -> tuple[float, list[str]]:
        columns = [
            self._normalize(column)
            for column in metadata.get("columns", [])
        ]
        numeric_columns = metadata.get("numeric_columns", []) or []
        categorical_columns = metadata.get("categorical_columns", []) or []
        datetime_columns = metadata.get("datetime_columns", []) or []
        signals = []
        score = 0.0

        if pattern_id == "time_performance_analysis":
            time_terms = [
                "duration",
                "durata",
                "elapsed",
                "tempo",
                "latency",
                "latenza",
                "resolution",
                "risoluzione",
                "response",
                "sla",
            ]
            if datetime_columns:
                score += 0.08
                signals.append("datetime_columns")
            if any(any(term in column for term in time_terms) for column in columns):
                score += 0.18
                signals.append("performance_column")

        elif pattern_id == "categorical_segmentation":
            if categorical_columns:
                score += 0.2
                signals.append("categorical_columns")

        elif pattern_id == "data_quality_audit":
            if metadata.get("missing_values"):
                score += 0.18
                signals.append("missing_values")
            if metadata.get("duplicate_rows"):
                score += 0.18
                signals.append("duplicate_rows")

        elif pattern_id == "operational_kpi_analysis":
            if numeric_columns:
                score += 0.12
                signals.append("numeric_columns")
            if datetime_columns:
                score += 0.08
                signals.append("datetime_columns")

        return min(score, 0.3), signals

    def _default_patterns(self) -> list[dict[str, Any]]:
        return [
            {
                "pattern_id": "time_performance_analysis",
                "name": "Analisi delle performance temporali",
                "description": (
                    "Valuta durata, distribuzione, trend, outlier e rispetto "
                    "di soglie operative o SLA."
                ),
                "trigger_keywords": [
                    "tempo",
                    "durata",
                    "latenza",
                    "performance",
                    "sla",
                    "risoluzione",
                    "risposta",
                    "degrado",
                    "percentile",
                    "p90",
                    "p95",
                    "p99",
                ],
                "recommended_metrics": [
                    "mean",
                    "median",
                    "p10",
                    "p25",
                    "p75",
                    "p90",
                    "p95",
                    "p99",
                    "iqr",
                    "standard_deviation",
                    "coefficient_of_variation",
                    "mad",
                    "z_score_outliers",
                    "modified_z_score_outliers",
                    "outlier_count",
                    "sla_breach_rate",
                ],
                "recommended_groupings": [
                    "periodo",
                    "categoria_operativa",
                    "priorita",
                    "owner",
                ],
                "recommended_charts": [
                    "time_series",
                    "box_plot",
                    "percentile_distribution",
                    "sla_breach_chart",
                ],
                "senior_analyst_notes": [
                    "Affiancare media e mediana per limitare la distorsione degli outlier.",
                    "Usare P90, P95 e P99 per descrivere la coda della distribuzione.",
                    "Confrontare i percentili con SLA e soglie operative esplicite.",
                    "Verificare degrado, stagionalita e cambi di livello nel tempo.",
                ],
                "confidence_score": 0.1,
                "recommended_analysis_steps": [
                    {
                        "title": "Statistiche robuste della durata",
                        "analysis_type": "advanced_statistical_summary",
                        "metric": "percentiles_dispersion_outliers",
                        "reason": "Descrivere centro, coda, dispersione robusta e valori estremi.",
                        "priority": 10,
                    },
                    {
                        "title": "Trend delle performance",
                        "analysis_type": "time_trend",
                        "metric": "performance_over_time",
                        "grouping": "periodo",
                        "reason": "Individuare degrado e variazioni temporali.",
                        "priority": 20,
                    },
                    {
                        "title": "Outlier e violazioni SLA",
                        "analysis_type": "threshold_and_outlier_analysis",
                        "metric": "sla_breach_rate",
                        "reason": "Quantificare casi estremi e superamenti soglia.",
                        "priority": 30,
                    },
                ],
            },
            {
                "pattern_id": "categorical_segmentation",
                "name": "Segmentazione categoriale",
                "description": (
                    "Confronta distribuzioni, concentrazioni e anomalie tra segmenti."
                ),
                "trigger_keywords": [
                    "segmenta",
                    "segmentazione",
                    "categoria",
                    "distribuzione",
                    "raggruppa",
                    "per stato",
                    "per cliente",
                    "per regione",
                    "per canale",
                    "top",
                ],
                "recommended_metrics": [
                    "count",
                    "share_percent",
                    "segment_rank",
                    "segment_variance",
                ],
                "recommended_groupings": [
                    "categoria",
                    "stato",
                    "cliente",
                    "regione",
                    "canale",
                ],
                "recommended_charts": [
                    "bar_chart",
                    "stacked_bar_chart",
                    "pareto_chart",
                    "segment_box_plot",
                ],
                "senior_analyst_notes": [
                    "Mostrare valore assoluto e quota percentuale di ogni segmento.",
                    "Evidenziare concentrazioni e segmenti con comportamento anomalo.",
                    "Confrontare segmenti omogenei evitando gruppi con campioni insufficienti.",
                ],
                "confidence_score": 0.1,
                "recommended_analysis_steps": [
                    {
                        "title": "Distribuzione per segmento",
                        "analysis_type": "count_occurrences",
                        "metric": "count_and_share",
                        "grouping": "categoria",
                        "reason": "Misurare peso e concentrazione dei segmenti.",
                        "priority": 10,
                    },
                    {
                        "title": "Top segmenti",
                        "analysis_type": "top_n",
                        "metric": "segment_rank",
                        "grouping": "categoria",
                        "reason": "Individuare i segmenti dominanti.",
                        "priority": 20,
                    },
                    {
                        "title": "Anomalie per segmento",
                        "analysis_type": "segment_anomaly_analysis",
                        "metric": "segment_variance",
                        "grouping": "categoria",
                        "reason": "Confrontare scostamenti tra gruppi.",
                        "priority": 30,
                    },
                ],
            },
            {
                "pattern_id": "data_quality_audit",
                "name": "Audit della qualita dati",
                "description": (
                    "Verifica completezza, unicita, formati e coerenza del dataset."
                ),
                "trigger_keywords": [
                    "qualita",
                    "quality",
                    "null",
                    "mancanti",
                    "missing",
                    "duplicati",
                    "doppioni",
                    "formato",
                    "incoerenti",
                    "colonne mancanti",
                    "audit",
                ],
                "recommended_metrics": [
                    "null_count",
                    "null_percent",
                    "duplicate_count",
                    "invalid_date_count",
                    "inconsistent_value_count",
                    "missing_critical_columns",
                ],
                "recommended_groupings": [
                    "colonna",
                    "tipo_errore",
                    "sorgente",
                ],
                "recommended_charts": [
                    "data_quality_scorecard",
                    "missing_values_bar",
                    "invalid_format_table",
                ],
                "senior_analyst_notes": [
                    "Separare problemi bloccanti da anomalie informative.",
                    "Misurare null e formati invalidi sia in valore assoluto sia percentuale.",
                    "Verificare prima le colonne critiche usate nei KPI e nei filtri.",
                ],
                "confidence_score": 0.1,
                "recommended_analysis_steps": [
                    {
                        "title": "Completezza del dataset",
                        "analysis_type": "null_detection",
                        "metric": "null_count_and_percent",
                        "grouping": "colonna",
                        "reason": "Individuare campi incompleti.",
                        "priority": 10,
                    },
                    {
                        "title": "Unicita dei record",
                        "analysis_type": "duplicate_detection",
                        "metric": "duplicate_count",
                        "reason": "Evitare distorsioni causate da record duplicati.",
                        "priority": 20,
                    },
                    {
                        "title": "Formati e valori incoerenti",
                        "analysis_type": "format_consistency_audit",
                        "metric": "invalid_values",
                        "grouping": "colonna",
                        "reason": "Validare date, domini e colonne critiche.",
                        "priority": 30,
                    },
                ],
            },
            {
                "pattern_id": "operational_kpi_analysis",
                "name": "Analisi KPI operativi",
                "description": (
                    "Sintetizza KPI, distribuzioni, trend e implicazioni operative."
                ),
                "trigger_keywords": [
                    "kpi",
                    "indicatore",
                    "indicatori",
                    "operativo",
                    "operativa",
                    "performance aziendale",
                    "produttivita",
                    "efficienza",
                    "panoramica",
                    "dashboard",
                    "andamento",
                ],
                "recommended_metrics": [
                    "total",
                    "mean",
                    "median",
                    "minimum",
                    "maximum",
                    "trend_change",
                    "target_variance",
                ],
                "recommended_groupings": [
                    "periodo",
                    "unita_operativa",
                    "owner",
                    "categoria",
                ],
                "recommended_charts": [
                    "kpi_cards",
                    "time_series",
                    "distribution_chart",
                    "target_variance_chart",
                ],
                "senior_analyst_notes": [
                    "Collegare ogni KPI a definizione, unita di misura e perimetro.",
                    "Affiancare livello corrente, trend e confronto con target.",
                    "Tradurre gli scostamenti in raccomandazioni operative verificabili.",
                ],
                "confidence_score": 0.1,
                "recommended_analysis_steps": [
                    {
                        "title": "KPI principali",
                        "analysis_type": "numeric_aggregation",
                        "metric": "total_mean_median",
                        "reason": "Quantificare livello e variabilita operativa.",
                        "priority": 10,
                    },
                    {
                        "title": "Distribuzione KPI",
                        "analysis_type": "numeric_distribution",
                        "metric": "distribution",
                        "reason": "Evitare conclusioni basate sulla sola media.",
                        "priority": 20,
                    },
                    {
                        "title": "Trend e azioni operative",
                        "analysis_type": "time_trend",
                        "metric": "trend_change",
                        "grouping": "periodo",
                        "reason": "Collegare andamento e raccomandazioni.",
                        "priority": 30,
                    },
                ],
            },
        ]

    def _keyword_matches(self, request: str, keyword: str) -> bool:
        normalized_keyword = self._normalize(keyword)
        if " " in normalized_keyword:
            return normalized_keyword in request
        return bool(re.search(rf"\b{re.escape(normalized_keyword)}\w*\b", request))

    def _normalize(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    def _unique(self, values: list[Any]) -> list[Any]:
        output = []
        for value in values:
            if value not in output:
                output.append(value)
        return output

    def _json_safe(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
