"""Motore locale per insight e report professionali deterministici."""

from __future__ import annotations

import json
import math
from typing import Any


class SeniorDataAnalystEngine:
    """Trasforma risultati deterministici in una relazione da data analyst."""

    def analyze(self, processed_data: dict, user_request: str = "") -> dict:
        """Genera insight locali senza chiamate a servizi esterni."""
        data = processed_data if isinstance(processed_data, dict) else {}
        summary = data.get("deterministic_summary") or {}
        results = self._collect_results(data)
        semantic_columns = data.get("semantic_columns") or {}
        intent_plan = data.get("analytical_intent_plan") or {}
        forbidden_columns = set(data.get("forbidden_columns") or intent_plan.get("forbidden_columns") or [])

        analysis = {
            "user_request": user_request,
            "analysis_source": "local_deterministic_engine",
            "dataset_profile": self._dataset_profile(summary, data),
            "key_findings": [],
            "kpi_summary": self._build_kpis(summary, results, semantic_columns),
            "trend_analysis": self._build_trends(summary, results, intent_plan),
            "anomaly_analysis": self._build_anomalies(summary, results, semantic_columns),
            "segmentation_analysis": self._build_segments(summary, results, forbidden_columns),
            "data_quality_notes": self._build_quality_notes(summary, results),
            "operational_recommendations": [],
            "semantic_columns": semantic_columns,
            "analytical_intent_plan": intent_plan,
            "primary_metric": data.get("primary_metric"),
            "time_axis": data.get("time_axis"),
            "segmentations": data.get("segmentations") or [],
            "forbidden_columns": list(forbidden_columns),
            "semantic_feature_plan": data.get("semantic_feature_plan") or {},
            "semantic_feature_results": data.get("semantic_feature_results") or {},
            "engineered_features": data.get("engineered_features") or [],
            "activation_time_analysis": self._build_activation_time_analysis(data),
            "temporal_concentration_results": data.get("temporal_concentration_results") or {},
            "analysis_plan": data.get("analysis_plan") or {},
            "execution_summary": data.get("execution_summary") or {},
            "detected_patterns": data.get("detected_patterns") or [],
            "knowledge_analysis_steps": data.get("knowledge_analysis_steps") or [],
            "learning_state": data.get("learning_state") or {},
            "learning_events": data.get("learning_events") or [],
            "analytical_strategy": data.get("analytical_strategy") or {},
            "analytical_reasoning_trace": data.get("analytical_reasoning_trace") or {},
            "advanced_statistical_results": data.get("advanced_statistical_results") or {},
            "anomaly_detection_results": data.get("anomaly_detection_results") or {},
            "root_cause_results": data.get("root_cause_results") or {},
            "domain_pack_context": data.get("domain_pack_context") or {},
        }
        analysis["methodological_notes"] = self._build_methodological_notes(
            analysis["detected_patterns"]
        )
        analysis["learning_reliability_notes"] = self._build_learning_reliability_notes(
            analysis["learning_state"],
            analysis["detected_patterns"],
        )
        analysis["key_findings"] = self._build_key_findings(analysis)
        analysis["operational_recommendations"] = self._build_recommendations(analysis)
        analysis["executive_summary"] = self.generate_executive_summary(analysis)
        analysis["final_report"] = self.generate_final_report(analysis)
        return self._json_safe(analysis)

    def generate_executive_summary(self, analysis: dict) -> str:
        """Produce una sintesi direzionale in massimo cinque bullet."""
        return self._bullet_list(self._build_executive_bullets(analysis))

    def _build_executive_bullets(self, analysis: dict) -> list[str]:
        profile = analysis.get("dataset_profile", {})
        rows = profile.get("row_count", 0)
        columns = profile.get("column_count", 0)
        activation = analysis.get("activation_time_analysis") or {}
        anomaly_summary = self._summarize_anomalies(analysis)
        recommendations = analysis.get("operational_recommendations") or []

        bullets = [
            (
                f"Analizzati {rows} record e {columns} colonne per misurare tempi, qualita dati e concentrazioni operative."
                if rows or columns
                else "Analisi completata sul perimetro disponibile; dimensione dataset non esposta nel payload."
            )
        ]
        if activation.get("status") == "computed":
            bullets.append(
                f"Record calcolabili per il tempo di attivazione: {activation.get('valid_count', 0)}; "
                f"mediana {self._fmt(activation.get('median'))} giorni e P95 {self._fmt(activation.get('p95'))} giorni."
            )
        elif analysis.get("key_findings"):
            bullets.append(str(analysis["key_findings"][0]))
        bullets.append(anomaly_summary["executive_note"])
        temporal = analysis.get("temporal_concentration_results") or {}
        if temporal.get("status") == "computed":
            bullets.append(
                "I tempi lunghi sono concentrati in giornate specifiche."
                if temporal.get("conclusion") == "concentrated"
                else "I tempi lunghi risultano distribuiti sul periodo osservato."
            )
        else:
            bullets.append("La concentrazione temporale non ha evidenza sufficiente o non e stata calcolata.")
        if recommendations:
            bullets.append(f"Prossima azione consigliata: {recommendations[0]}")
        return bullets[:5]

    def generate_final_report(self, analysis: dict) -> str:
        """Compone un report Markdown business-first ed esportabile."""
        profile = analysis.get("dataset_profile", {})
        request = analysis.get("user_request") or "Analisi generale dei dati"
        sections = [
            "# Report business",
            "",
            f"**Obiettivo:** {request}",
            f"**Perimetro:** {profile.get('row_count', 0)} record, {profile.get('column_count', 0)} colonne.",
            "",
            "## Executive Summary",
            self._bullet_list(self._build_executive_bullets(analysis)),
            "",
            "## KPI principali",
            self._format_business_kpi_table(analysis),
            "",
            "## Interpretazione business",
            self._format_business_interpretation(analysis),
            "",
            "## Concentrazione temporale dei tempi lunghi",
            self._format_temporal_concentration_table(
                analysis.get("temporal_concentration_results", {})
            ),
            "",
            "## Segmentazione utile",
            self._format_business_segments(analysis.get("segmentation_analysis", [])),
            "",
            "## Anomalie rilevate",
            self._format_anomaly_summary(analysis),
            self._format_detected_anomalies(
                analysis.get("anomaly_detection_results", {})
            ),
            "",
            "## Possibili cause radice",
            self._format_root_causes(analysis.get("root_cause_results", {})),
            "",
            "## Raccomandazioni operative",
            self._numbered_list((analysis.get("operational_recommendations") or [])[:5]),
            "",
            "## Best practice metodologiche",
            self._bullet_list((analysis.get("methodological_notes") or [])[:3]),
            "",
            "## Appendice tecnica",
            self._format_technical_appendix(analysis),
        ]
        return "\n".join(sections)

    def _format_business_kpi_table(self, analysis: dict) -> str:
        rows = self._business_kpi_rows(analysis)
        lines = ["| KPI | Valore |", "|---|---:|"]
        lines.extend(f"| {name} | {self._fmt(value)} |" for name, value in rows)
        return "\n".join(lines)

    def _business_kpi_rows(self, analysis: dict) -> list[tuple[str, Any]]:
        profile = analysis.get("dataset_profile", {})
        activation = analysis.get("activation_time_analysis") or {}
        anomaly_summary = self._summarize_anomalies(analysis)
        rows = [
            ("Record analizzati", profile.get("row_count", 0)),
            ("Record calcolabili", activation.get("valid_count", "n/a")),
            ("Media", activation.get("mean", "n/a")),
            ("Mediana", activation.get("median", "n/a")),
            ("P75", activation.get("p75", "n/a")),
            ("P90", activation.get("p90", "n/a")),
            ("P95", activation.get("p95", "n/a")),
            ("P99", activation.get("p99", "n/a")),
            ("Outlier count", anomaly_summary["positive_count"]),
            ("Negative duration count", anomaly_summary["negative_duration_count"]),
        ]
        if activation.get("status") != "computed":
            for kpi in analysis.get("kpi_summary", []):
                name = kpi.get("name")
                if name in {"Righe analizzate", "Record analizzati"}:
                    rows[0] = ("Record analizzati", kpi.get("value", rows[0][1]))
                elif rows[2][1] == "n/a" and str(name).lower().startswith("media"):
                    rows[2] = ("Media", kpi.get("value"))
        return rows

    def _format_business_interpretation(self, analysis: dict) -> str:
        activation = analysis.get("activation_time_analysis") or {}
        anomaly_summary = self._summarize_anomalies(analysis)
        if activation.get("status") != "computed":
            return (
                "- Non e disponibile una metrica di durata calcolata: interpretare i KPI come indicatori descrittivi del dataset.\n"
                f"- Segnale principale: {anomaly_summary['business_note']}"
            )
        lines = [
            (
                f"- La media ({self._fmt(activation.get('mean'))}) indica il valore medio, ma puo essere spostata da pochi casi estremi."
            ),
            (
                f"- La mediana ({self._fmt(activation.get('median'))}) descrive il caso tipico: meta dei record calcolabili sta sotto questo valore."
            ),
            (
                f"- Il P95 ({self._fmt(activation.get('p95'))}) rappresenta la coda operativa: il 5% dei casi supera questa durata."
            ),
            f"- Lettura del segnale: {anomaly_summary['business_note']}",
        ]
        if activation.get("negative_duration_count", 0):
            lines.append(
                "- Le durate negative vanno trattate come possibile problema di qualita dati, non come tempi lunghi reali."
            )
        return "\n".join(lines)

    def _format_temporal_concentration_table(self, results: dict[str, Any]) -> str:
        if not isinstance(results, dict) or results.get("status") not in {"computed", "insufficient_evidence"}:
            return "- Analisi non disponibile o non calcolabile."
        if results.get("conclusion") == "insufficient_evidence":
            return "- Conclusione: evidenza insufficiente per stabilire concentrazione temporale."
        lines = ["| Giorno | Record | Outlier | Ratio | Nota |", "|---|---:|---:|---:|---|"]
        top_days = results.get("top_days") or []
        for item in top_days[:5]:
            ratio = item.get("outlier_ratio")
            note = "giorno critico" if self._is_number(ratio) and float(ratio) >= 0.5 else "da monitorare"
            lines.append(
                f"| {item.get('day', 'n/a')} | {item.get('total_count', 0)} | "
                f"{item.get('outlier_count', 0)} | {self._fmt(ratio)} | {note} |"
            )
        if len(lines) == 2:
            lines.append("| n/a | 0 | 0 | n/a | nessun giorno critico disponibile |")
        conclusion = results.get("conclusion")
        label = "concentrati" if conclusion == "concentrated" else "distribuiti"
        lines.append("")
        lines.append(f"- Conclusione: tempi lunghi {label}.")
        return "\n".join(lines)

    def _format_business_segments(self, segments: list[dict[str, Any]]) -> str:
        useful = [
            segment for segment in segments
            if self._is_useful_segment_column(segment.get("column"), segment)
        ][:5]
        if not useful:
            return "- Nessuna segmentazione sufficientemente informativa sul perimetro analizzato."
        lines = ["| Dimensione | Segmento principale | Valore | Quota |", "|---|---|---:|---:|"]
        for segment in useful:
            lines.append(
                f"| {segment.get('column') or 'n/a'} | {segment.get('leading_segment')} | "
                f"{self._fmt(segment.get('leading_value'))} | {self._fmt(segment.get('leading_share_percent'))}% |"
            )
        return "\n".join(lines)

    def _format_anomaly_summary(self, analysis: dict) -> str:
        summary = self._summarize_anomalies(analysis)
        lines = [
            f"- Anomalie positive rilevate: {summary['positive_count']}.",
            f"- Durate negative rilevate: {summary['negative_duration_count']} (possibile qualita dati).",
            f"- Soglia usata: {summary['threshold']}.",
            f"- Min/Max osservati: {summary['min_value']} / {summary['max_value']}.",
        ]
        if summary["examples"]:
            lines.append("- Esempi principali: " + "; ".join(summary["examples"][:5]) + ".")
        return "\n".join(lines)

    def _format_technical_appendix(self, analysis: dict) -> str:
        profile = analysis.get("dataset_profile", {})
        source = analysis.get("analysis_source", "local_deterministic_engine")
        mode = analysis.get("execution_summary", {}).get("source", "n/a")
        return "\n".join([
            f"- Fonte analisi: {source}.",
            f"- Esecuzione: {mode}.",
            f"- Colonne numeriche considerate: {len(profile.get('numeric_columns', []))}.",
            f"- Colonne categoriali considerate: {len(profile.get('categorical_columns', []))}.",
            "- Nessun dump tecnico raw incluso nel report business.",
        ])

    def _summarize_anomalies(self, analysis: dict) -> dict[str, Any]:
        activation = analysis.get("activation_time_analysis") or {}
        detection = analysis.get("anomaly_detection_results") or {}
        detected = detection.get("anomalies") if isinstance(detection, dict) else []
        positive_count = 0
        quality_count = 0
        examples = []
        threshold = "n/a"
        values = []
        for item in analysis.get("anomaly_analysis") or []:
            if not isinstance(item, dict):
                continue
            anomaly_type = item.get("type")
            if anomaly_type == "potential_extreme_value":
                positive_count += 1
                value = item.get("value")
                if isinstance(value, dict):
                    for key in ("min", "max", "mean"):
                        if self._is_number(value.get(key)):
                            values.append(float(value[key]))
            else:
                quality_count += 1
            if item.get("summary") and len(examples) < 5:
                examples.append(str(item.get("summary")))
        for item in detected or []:
            if not isinstance(item, dict):
                continue
            observed = item.get("observed_value")
            if self._is_number(observed):
                values.append(float(observed))
                if float(observed) >= 0:
                    positive_count += 1
            else:
                positive_count += 1
            if item.get("recommendation") and len(examples) < 5:
                examples.append(str(item.get("recommendation")))
            evidence = item.get("evidence") or {}
            if threshold == "n/a" and isinstance(evidence, dict):
                threshold = evidence.get("threshold") or evidence.get("upper_bound") or threshold
        positive_count = max(positive_count, int(activation.get("outlier_count", 0) or 0))
        negative_count = int(activation.get("negative_duration_count", 0) or 0)
        for value in (activation.get("mean"), activation.get("median"), activation.get("p95"), activation.get("p99")):
            if self._is_number(value):
                values.append(float(value))
        business_note = (
            "il dato suggerisce prima una verifica di qualita sulle date negative."
            if negative_count
            else "il dato suggerisce controlli di qualita dati prima del consolidamento dei KPI."
            if quality_count
            else "il dato suggerisce una coda operativa da monitorare sui casi estremi."
            if positive_count
            else "non emergono segnali anomali rilevanti dai controlli disponibili."
        )
        executive_note = (
            f"Rischio principale: {negative_count} durate negative da verificare come qualita dati."
            if negative_count
            else f"Rischio principale: {quality_count} segnali di qualita dati da correggere o validare."
            if quality_count
            else f"Rischio principale: {positive_count} anomalie positive o outlier da verificare."
            if positive_count
            else "Rischio principale: nessuna anomalia critica nei controlli disponibili."
        )
        return {
            "positive_count": positive_count,
            "negative_duration_count": negative_count,
            "threshold": self._fmt(threshold),
            "min_value": self._fmt(min(values) if values else "n/a"),
            "max_value": self._fmt(max(values) if values else "n/a"),
            "examples": examples,
            "business_note": business_note,
            "executive_note": executive_note,
        }

    def _collect_results(self, data: dict) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        direct = data.get("deterministic_results")
        if isinstance(direct, dict) and direct:
            collected.append({
                "title": "Analisi deterministica principale",
                "step_id": "single-plan",
                "result": direct,
            })

        for item in data.get("autonomous_analysis_results") or []:
            if not isinstance(item, dict) or item.get("status") not in {None, "completed"}:
                continue
            result = item.get("result")
            if isinstance(result, dict) and result:
                collected.append({
                    "title": item.get("title") or item.get("step_id") or "Analisi autonoma",
                    "step_id": item.get("step_id", ""),
                    "result": result,
                })
        return collected

    def _dataset_profile(self, summary: dict, data: dict) -> dict[str, Any]:
        autonomous_plan = data.get("autonomous_analysis_plan") or {}
        autonomous_profile = autonomous_plan.get("dataset_profile") or {}
        return {
            "row_count": int(summary.get("row_count", autonomous_profile.get("row_count", 0)) or 0),
            "column_count": int(
                summary.get("column_count", autonomous_profile.get("column_count", 0)) or 0
            ),
            "columns": summary.get("columns", autonomous_profile.get("columns", [])) or [],
            "numeric_columns": summary.get(
                "numeric_columns", autonomous_profile.get("numeric_columns", [])
            ) or [],
            "categorical_columns": summary.get(
                "categorical_columns", autonomous_profile.get("categorical_columns", [])
            ) or [],
            "datetime_columns": summary.get(
                "datetime_columns", autonomous_profile.get("datetime_columns", [])
            ) or [],
        }

    def _build_kpis(
        self,
        summary: dict,
        results: list[dict[str, Any]],
        semantic_columns: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        kpis: list[dict[str, Any]] = []
        if summary.get("row_count") is not None:
            kpis.append(self._kpi("Righe analizzate", summary.get("row_count", 0), "volume"))
        if summary.get("column_count") is not None:
            kpis.append(self._kpi("Colonne analizzate", summary.get("column_count", 0), "struttura"))

        for column, stats in list((summary.get("numeric_summary") or {}).items())[:8]:
            if not self._is_business_metric(column, semantic_columns):
                continue
            for metric, label in (("mean", "Media"), ("sum", "Totale"), ("min", "Minimo"), ("max", "Massimo")):
                if stats.get(metric) is not None:
                    kpis.append(
                        self._kpi(f"{label} {column}", stats[metric], "metrica_numerica", column)
                    )

        for item in results:
            result = item["result"]
            analysis_type = result.get("analysis_type")
            if analysis_type == "duration_between_dates" and result.get("average_hours") is not None:
                kpis.append(
                    self._kpi(
                        "Durata media",
                        result["average_hours"],
                        "ore",
                        f"{result.get('start_column')} -> {result.get('end_column')}",
                    )
                )
            elif analysis_type == "numeric_aggregation" and result.get("result") is not None:
                kpis.append(
                    self._kpi(
                        f"{result.get('aggregation', 'Valore')} {result.get('value_column', '')}".strip(),
                        result["result"],
                        "aggregazione",
                    )
                )
        return self._deduplicate(kpis, ("name", "value"))[:30]

    def _build_trends(
        self,
        summary: dict,
        results: list[dict[str, Any]],
        intent_plan: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        trends: list[dict[str, Any]] = []
        plan = intent_plan if isinstance(intent_plan, dict) else {}
        preferred_time_axis = plan.get("time_axis")
        primary_metric = plan.get("primary_metric")
        for item in results:
            result = item["result"]
            if preferred_time_axis and result.get("time_column") != preferred_time_axis:
                continue
            if primary_metric and result.get("value_column") not in {primary_metric, None}:
                continue
            points = result.get("points")
            if not isinstance(points, list) or not points:
                continue
            numeric_points = [
                point for point in points
                if isinstance(point, dict) and self._is_number(point.get("value"))
            ]
            if not numeric_points:
                continue
            first = float(numeric_points[0]["value"])
            last = float(numeric_points[-1]["value"])
            change = last - first
            change_percent = None
            if first != 0 and first * last >= 0 and abs(first) >= 1:
                change_percent = round(change / abs(first) * 100, 2)
            direction = "crescente" if change > 0 else "decrescente" if change < 0 else "stabile"
            peak = max(numeric_points, key=lambda point: float(point["value"]))
            low = min(numeric_points, key=lambda point: float(point["value"]))
            summary_text = (
                f"Il trend su {result.get('time_column', 'asse temporale')} è {direction}: "
                f"da {self._fmt(first)} a {self._fmt(last)}"
                + (
                    f" ({change_percent:+.2f}%)."
                    if change_percent is not None
                    else ", senza percentuale riportata per evitare letture fuorvianti."
                )
            )
            trends.append({
                "title": item["title"],
                "time_column": result.get("time_column"),
                "aggregation": result.get("aggregation"),
                "direction": direction,
                "first_value": first,
                "last_value": last,
                "absolute_change": round(change, 4),
                "percentage_change": change_percent,
                "peak_period": peak.get("period"),
                "peak_value": peak.get("value"),
                "minimum_period": low.get("period"),
                "minimum_value": low.get("value"),
                "summary": summary_text,
            })

        if not trends:
            for column, time_range in (summary.get("time_ranges") or {}).items():
                if preferred_time_axis and column != preferred_time_axis:
                    continue
                trends.append({
                    "title": f"Copertura temporale {column}",
                    "time_column": column,
                    "direction": "non_calcolabile",
                    "summary": (
                        f"La colonna {column} copre il periodo da {time_range.get('min')} "
                        f"a {time_range.get('max')} su {time_range.get('valid_values', 0)} valori validi."
                    ),
                })
        return trends

    def _build_anomalies(
        self,
        summary: dict,
        results: list[dict[str, Any]],
        semantic_columns: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        for column, stats in (summary.get("missing_values") or {}).items():
            percent = float(stats.get("percent", 0) or 0)
            anomalies.append({
                "type": "missing_values",
                "severity": "alta" if percent >= 20 else "media" if percent >= 5 else "bassa",
                "column": column,
                "value": int(stats.get("count", 0) or 0),
                "summary": f"{column}: {stats.get('count', 0)} valori mancanti ({percent:.2f}%).",
            })

        duplicate_rows = int(summary.get("duplicate_rows", 0) or 0)
        if duplicate_rows:
            anomalies.append({
                "type": "duplicate_rows",
                "severity": "media",
                "value": duplicate_rows,
                "summary": f"Rilevate {duplicate_rows} righe duplicate.",
            })

        for column, stats in (summary.get("numeric_summary") or {}).items():
            if not self._is_business_metric(column, semantic_columns):
                continue
            mean = stats.get("mean")
            std = stats.get("std")
            minimum = stats.get("min")
            maximum = stats.get("max")
            if not all(self._is_number(value) for value in (mean, std, minimum, maximum)):
                continue
            mean_value = float(mean)
            std_value = float(std)
            min_value = float(minimum)
            max_value = float(maximum)
            outside_three_sigma = std_value > 0 and (
                max_value > mean_value + 3 * std_value
                or min_value < mean_value - 3 * std_value
            )
            extreme_ratio = mean_value != 0 and max_value / abs(mean_value) >= 5
            if outside_three_sigma or extreme_ratio:
                anomalies.append({
                    "type": "potential_extreme_value",
                    "severity": "media",
                    "column": column,
                    "value": {"min": minimum, "max": maximum, "mean": mean, "std": std},
                    "summary": (
                        f"{column}: il range mostra un estremo potenzialmente anomalo "
                        "rispetto alla distribuzione sintetica disponibile."
                    ),
                })

        for item in results:
            result = item["result"]
            if result.get("analysis_type") == "null_detection":
                for stats in result.get("columns_with_nulls") or []:
                    column = stats.get("column")
                    if not column or any(
                        anomaly.get("type") == "missing_values"
                        and anomaly.get("column") == column
                        for anomaly in anomalies
                    ):
                        continue
                    percent = float(stats.get("null_percent", 0) or 0)
                    anomalies.append({
                        "type": "missing_values",
                        "severity": "alta" if percent >= 20 else "media" if percent >= 5 else "bassa",
                        "column": column,
                        "value": int(stats.get("null_count", 0) or 0),
                        "summary": (
                            f"{column}: {stats.get('null_count', 0)} valori mancanti "
                            f"({percent:.2f}%)."
                        ),
                    })
            if result.get("analysis_type") == "duplicate_detection":
                duplicates = int(result.get("duplicate_rows", 0) or 0)
                if duplicates and not any(
                    anomaly["type"] == "duplicate_rows" for anomaly in anomalies
                ):
                    anomalies.append({
                        "type": "duplicate_rows",
                        "severity": "media",
                        "value": duplicates,
                        "summary": f"Rilevate {duplicates} righe duplicate.",
                    })
        return anomalies

    def _build_segments(
        self,
        summary: dict,
        results: list[dict[str, Any]],
        forbidden_columns: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
        forbidden = forbidden_columns or set()
        for item in results:
            result = item["result"]
            values = result.get("counts") or result.get("top") or result.get("groups")
            if not isinstance(values, list) or not values:
                continue
            normalized = []
            for entry in values:
                if not isinstance(entry, dict):
                    continue
                if "group" in entry:
                    label = entry.get("group")
                    metric = entry.get("value")
                else:
                    label = entry.get("value")
                    metric = entry.get("count", entry.get("metric"))
                if label is not None and self._is_number(metric):
                    normalized.append({"segment": label, "value": metric})
            if not normalized:
                continue
            total = sum(float(entry["value"]) for entry in normalized)
            leader = max(normalized, key=lambda entry: float(entry["value"]))
            share = round(float(leader["value"]) / total * 100, 2) if total else None
            column = result.get("target_column") or result.get("group_by_column")
            if column in forbidden or not self._is_useful_segment_column(column, {"segments": normalized}):
                continue
            segments.append({
                "title": item["title"],
                "column": column,
                "leading_segment": leader["segment"],
                "leading_value": leader["value"],
                "leading_share_percent": share,
                "segments": normalized[:10],
                "summary": (
                    f"Il segmento dominante per {column or 'la dimensione analizzata'} è "
                    f"{leader['segment']} con valore {self._fmt(leader['value'])}"
                    + (f" ({share:.2f}% del totale rappresentato)." if share is not None else ".")
                ),
            })

        if not segments:
            for column, stats in list((summary.get("categorical_summary") or {}).items())[:5]:
                if column in forbidden:
                    continue
                top_values = stats.get("top_values") or {}
                if not top_values:
                    continue
                values = [{"segment": key, "value": value} for key, value in top_values.items()]
                total = sum(float(entry["value"]) for entry in values)
                leader = max(values, key=lambda entry: float(entry["value"]))
                share = round(float(leader["value"]) / total * 100, 2) if total else None
                if not self._is_useful_segment_column(
                    column,
                    {"segments": values, "leading_share_percent": share},
                ):
                    continue
                segments.append({
                    "title": f"Distribuzione di {column}",
                    "column": column,
                    "leading_segment": leader["segment"],
                    "leading_value": leader["value"],
                    "leading_share_percent": share,
                    "segments": values,
                    "summary": (
                        f"Tra i valori principali di {column}, {leader['segment']} è il più frequente "
                        f"con {self._fmt(leader['value'])} occorrenze."
                    ),
                })
        return segments

    def _build_quality_notes(self, summary: dict, results: list[dict[str, Any]]) -> list[str]:
        rows = int(summary.get("row_count", 0) or 0)
        result_nulls = max(
            (
                int(item["result"].get("total_nulls", 0) or 0)
                for item in results
                if item["result"].get("analysis_type") == "null_detection"
            ),
            default=0,
        )
        result_duplicates = max(
            (
                int(item["result"].get("duplicate_rows", 0) or 0)
                for item in results
                if item["result"].get("analysis_type") == "duplicate_detection"
            ),
            default=0,
        )
        notes = [
            f"Il dataset contiene {rows} righe e {int(summary.get('column_count', 0) or 0)} colonne."
        ]
        missing = summary.get("missing_values") or {}
        total_missing = max(
            sum(int(stats.get("count", 0) or 0) for stats in missing.values()),
            result_nulls,
        )
        if total_missing:
            notes.append(
                f"Sono presenti {total_missing} celle mancanti distribuite su {len(missing)} colonne."
            )
        else:
            notes.append("Il riepilogo deterministico non rileva valori mancanti.")
        duplicates = max(int(summary.get("duplicate_rows", 0) or 0), result_duplicates)
        notes.append(
            f"Sono presenti {duplicates} righe duplicate."
            if duplicates
            else "Il riepilogo deterministico non rileva righe duplicate."
        )
        if not summary:
            notes.append(
                "Il profilo completo del dataframe non è disponibile; le conclusioni usano i risultati eseguiti."
            )
        return notes

    def _build_key_findings(self, analysis: dict) -> list[str]:
        findings: list[str] = []
        profile = analysis["dataset_profile"]
        findings.append(
            f"Perimetro disponibile: {profile.get('row_count', 0)} righe, "
            f"{profile.get('column_count', 0)} colonne, "
            f"{len(profile.get('numeric_columns', []))} metriche numeriche e "
            f"{len(profile.get('categorical_columns', []))} dimensioni categoriali."
        )
        activation = analysis.get("activation_time_analysis") or {}
        if activation.get("status") == "computed":
            findings.append(
                f"Tempi di attivazione calcolabili su {activation.get('valid_count', 0)} record: "
                f"mediana {self._fmt(activation.get('median'))} giorni, "
                f"P95 {self._fmt(activation.get('p95'))} giorni."
            )
        temporal = analysis.get("temporal_concentration_results") or {}
        if temporal.get("status") == "computed":
            conclusion = temporal.get("conclusion")
            if conclusion == "concentrated":
                findings.append(
                    f"I tempi lunghi risultano concentrati in poche giornate: "
                    f"{len(temporal.get('top_days') or [])} giornate critiche principali."
                )
            elif conclusion == "distributed":
                findings.append(
                    "I tempi lunghi risultano distribuiti e non riconducibili a singole giornate."
                )
        findings.extend(item["summary"] for item in analysis["segmentation_analysis"][:3])
        findings.extend(item["summary"] for item in analysis["trend_analysis"][:2])
        findings.extend(item["summary"] for item in analysis["anomaly_analysis"][:3])
        return findings

    def _build_recommendations(self, analysis: dict) -> list[str]:
        recommendations: list[str] = []
        anomalies = analysis["anomaly_analysis"]
        if any(item["type"] == "missing_values" for item in anomalies):
            recommendations.append(
                "Definire regole di imputazione o esclusione per i valori mancanti prima di usare i KPI operativi."
            )
        if any(item["type"] == "duplicate_rows" for item in anomalies):
            recommendations.append(
                "Verificare le chiavi logiche e deduplicare i record prima di consolidare i risultati."
            )
        if any(item["type"] == "potential_extreme_value" for item in anomalies):
            recommendations.append(
                "Validare gli estremi numerici rispetto a soglie di business e distinguere errori da eventi reali."
            )
        for trend in analysis["trend_analysis"]:
            if trend.get("direction") == "crescente":
                recommendations.append(
                    f"Monitorare la crescita osservata su {trend.get('time_column') or 'asse temporale'} "
                    "e confrontarla con capacità, target e stagionalità."
                )
            elif trend.get("direction") == "decrescente":
                recommendations.append(
                    f"Analizzare le cause della flessione su {trend.get('time_column') or 'asse temporale'} "
                    "e verificare se il calo è atteso o operativo."
                )
        for segment in analysis["segmentation_analysis"]:
            share = segment.get("leading_share_percent")
            if self._is_number(share) and float(share) >= 60:
                recommendations.append(
                    f"Valutare la concentrazione su {segment.get('leading_segment')} "
                    f"nella dimensione {segment.get('column') or 'analizzata'} ({share:.2f}%)."
                )
        pattern_ids = {
            pattern.get("pattern_id")
            for pattern in analysis.get("detected_patterns", [])
        }
        if "time_performance_analysis" in pattern_ids:
            recommendations.append(
                "Integrare media, mediana e percentili P75/P90/P95/P99 prima di valutare SLA e degrado."
            )
        if "categorical_segmentation" in pattern_ids:
            recommendations.append(
                "Confrontare numerosita e quota percentuale dei segmenti, isolando gruppi con campioni insufficienti."
            )
        if "data_quality_audit" in pattern_ids:
            recommendations.append(
                "Rendere bloccanti i controlli sulle colonne critiche prima di consolidare KPI e report."
            )
        if "operational_kpi_analysis" in pattern_ids:
            recommendations.append(
                "Associare ogni KPI a definizione, unita di misura, target e responsabile operativo."
            )
        for cause in (analysis.get("root_cause_results") or {}).get("possible_causes", [])[:3]:
            if not isinstance(cause, dict):
                continue
            for action in (cause.get("recommended_actions") or [])[:2]:
                recommendations.append(
                    f"Verifica root cause {cause.get('cause_id', 'n/a')}: {action}"
                )
        if not recommendations:
            recommendations.append(
                "Confermare i KPI con i responsabili di business e impostare un monitoraggio periodico."
            )
        recommendations.append(
            "Raccogliere feedback sull'utilità dell'analisi per migliorare il riuso dei pattern analitici."
        )
        return list(dict.fromkeys(recommendations))[:5]

    def _build_methodological_notes(self, patterns: list[dict[str, Any]]) -> list[str]:
        notes = []
        for pattern in patterns:
            for note in pattern.get("senior_analyst_notes", []):
                if note not in notes:
                    notes.append(note)
        if not notes:
            notes.append(
                "Applicare solo metriche coerenti con schema, granularita e qualita dei dati disponibili."
            )
        return notes

    def _build_learning_reliability_notes(
        self,
        learning_state: dict[str, Any],
        patterns: list[dict[str, Any]],
    ) -> list[str]:
        notes = []
        state_patterns = {}
        if isinstance(learning_state, dict):
            for item in learning_state.get("patterns", []) or []:
                if isinstance(item, dict) and item.get("pattern_id"):
                    state_patterns[item["pattern_id"]] = item

        for pattern in patterns or []:
            pattern_id = pattern.get("pattern_id")
            learning = pattern.get("learning") or state_patterns.get(pattern_id) or {}
            status = learning.get("status")
            confidence = learning.get(
                "confidence_score",
                pattern.get("confidence_score"),
            )
            if status == "promoted":
                notes.append(
                    f"Pattern {pattern_id} ad alta affidabilita locale "
                    f"(confidence {self._fmt(confidence)}): prioritario nel riuso."
                )
            elif status == "demoted":
                notes.append(
                    f"Pattern {pattern_id} a bassa affidabilita locale "
                    f"(confidence {self._fmt(confidence)}): da usare con cautela."
                )

        if isinstance(learning_state, dict):
            for pattern_id in learning_state.get("promoted_pattern_ids", []) or []:
                if not any(pattern_id in note for note in notes):
                    notes.append(
                        f"Pattern {pattern_id} promosso dal Learning Engine per feedback positivo ricorrente."
                    )
            for pattern_id in learning_state.get("demoted_pattern_ids", []) or []:
                if not any(pattern_id in note for note in notes):
                    notes.append(
                        f"Pattern {pattern_id} declassato dal Learning Engine per feedback negativo o confidence bassa."
                    )
        if not notes:
            notes.append(
                "Non sono ancora disponibili evidenze di apprendimento sufficienti sui pattern rilevati."
            )
        return notes

    def _build_activation_time_analysis(self, data: dict[str, Any]) -> dict[str, Any]:
        summary = data.get("deterministic_summary") or {}
        column = "TEMPO_ATTIVAZIONE_GIORNI"
        stats = (summary.get("numeric_summary") or {}).get(column)
        if not isinstance(stats, dict):
            return {"status": "not_available"}

        feature = {}
        for item in (data.get("semantic_feature_results") or {}).get("features", []) or []:
            if item.get("feature_name") == column:
                feature = item
                break

        advanced = data.get("advanced_statistical_results") or {}
        advanced_column = (advanced.get("numeric_analysis") or {}).get(column) or {}
        percentiles = advanced_column.get("percentiles") or {}
        dispersion = advanced_column.get("dispersion") or {}
        outliers = advanced_column.get("outliers") or {}
        iqr_outliers = (outliers.get("iqr") or {}).get("outlier_count", 0)

        p75 = percentiles.get("p75")
        p95 = percentiles.get("p95")
        median = stats.get("median", percentiles.get("p50"))
        mean = stats.get("mean")
        long_tail = (
            self._is_number(p95)
            and self._is_number(median)
            and float(median) > 0
            and float(p95) / float(median) >= 2
        )
        return {
            "status": "computed",
            "feature_name": column,
            "source_columns": feature.get("source_columns", {}),
            "valid_count": feature.get("valid_count", stats.get("count", 0)),
            "missing_count": feature.get("missing_count", stats.get("missing", 0)),
            "negative_duration_count": feature.get("negative_duration_count", 0),
            "mean": mean,
            "median": median,
            "p75": p75,
            "p90": percentiles.get("p90"),
            "p95": p95,
            "p99": percentiles.get("p99"),
            "iqr": dispersion.get("iqr"),
            "mad": dispersion.get("mad"),
            "outlier_count": iqr_outliers,
            "long_tail": long_tail,
        }

    def _format_activation_time_analysis(self, analysis: dict[str, Any]) -> str:
        if not isinstance(analysis, dict) or analysis.get("status") != "computed":
            return "- Feature TEMPO_ATTIVAZIONE_GIORNI non disponibile o non richiesta."
        sources = analysis.get("source_columns") or {}
        lines = [
            f"- Feature: **{analysis.get('feature_name')}**.",
            (
                f"- Colonne sorgente: {sources.get('start', 'n/a')} -> "
                f"{sources.get('end', 'n/a')}."
            ),
            (
                f"- Record calcolabili: {analysis.get('valid_count', 0)}; "
                f"mancanti/non parsabili: {analysis.get('missing_count', 0)}; "
                f"durate negative: {analysis.get('negative_duration_count', 0)}."
            ),
            (
                f"- Media {self._fmt(analysis.get('mean'))} giorni; "
                f"mediana {self._fmt(analysis.get('median'))} giorni; "
                f"P75 {self._fmt(analysis.get('p75'))}; P90 {self._fmt(analysis.get('p90'))}; "
                f"P95 {self._fmt(analysis.get('p95'))}; P99 {self._fmt(analysis.get('p99'))}."
            ),
            (
                f"- Variabilita: IQR {self._fmt(analysis.get('iqr'))}, "
                f"MAD {self._fmt(analysis.get('mad'))}, outlier IQR {analysis.get('outlier_count', 0)}."
            ),
            (
                "- La distribuzione mostra una coda lunga: il P95 è almeno il doppio della mediana."
                if analysis.get("long_tail")
                else "- Non emerge una coda lunga estrema dal rapporto P95/mediana."
            ),
        ]
        return "\n".join(lines)

    def _format_temporal_concentration(self, results: dict[str, Any]) -> str:
        if not isinstance(results, dict) or results.get("status") not in {"computed", "insufficient_evidence"}:
            return "- Analisi di concentrazione temporale non richiesta o non calcolabile."
        if results.get("conclusion") == "insufficient_evidence":
            return "- Evidenze insufficienti per stabilire se i tempi lunghi siano concentrati in giornate specifiche."
        top_days = results.get("top_days") or []
        if results.get("conclusion") == "concentrated":
            opening = f"- I tempi lunghi risultano concentrati in {len(top_days)} giornate principali."
        else:
            opening = "- I tempi lunghi risultano distribuiti e non riconducibili a singole giornate."
        lines = [
            opening,
            (
                f"- Soglia outlier: {self._fmt(results.get('outlier_threshold'))} "
                f"su {results.get('metric')} per {results.get('time_axis')}; "
                f"outlier totali: {results.get('outlier_count', 0)}."
            ),
        ]
        for item in top_days[:5]:
            lines.append(
                f"- {item.get('day')}: {item.get('outlier_count')} outlier "
                f"su {item.get('total_count')} record "
                f"(ratio {self._fmt(item.get('outlier_ratio'))})."
            )
        return "\n".join(lines)

    def _kpi(self, name: str, value: Any, category: str, context: str | None = None) -> dict:
        return {"name": name, "value": value, "category": category, "context": context}

    def _deduplicate(self, items: list[dict], keys: tuple[str, ...]) -> list[dict]:
        seen = set()
        output = []
        for item in items:
            marker = tuple(json.dumps(item.get(key), sort_keys=True, default=str) for key in keys)
            if marker not in seen:
                seen.add(marker)
                output.append(item)
        return output

    def _bullet_list(self, items: list[Any]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- Nessuna evidenza disponibile."

    def _numbered_list(self, items: list[Any]) -> str:
        return (
            "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))
            if items
            else "1. Nessuna raccomandazione disponibile."
        )

    def _format_kpis(self, kpis: list[dict[str, Any]]) -> str:
        if not kpis:
            return "- Nessun KPI deterministico disponibile."
        return "\n".join(
            f"- **{item.get('name')}:** {self._fmt(item.get('value'))}"
            + (f" ({item.get('context')})" if item.get("context") else "")
            for item in kpis
        )

    def _format_structured_items(self, items: list[dict[str, Any]], empty: str) -> str:
        if not items:
            return f"- {empty}"
        return "\n".join(f"- {item.get('summary', 'Elemento sintetico disponibile.')}" for item in items)

    def _format_analytical_strategy(self, strategy: dict[str, Any]) -> str:
        if not isinstance(strategy, dict) or not strategy:
            return "- Strategia analitica locale non disponibile."
        lines = [
            f"- Strategy ID: {strategy.get('strategy_id', 'n/a')}",
            f"- Confidence: {self._fmt(strategy.get('confidence_score', 0))}",
        ]
        for step in (strategy.get("recommended_sequence") or [])[:6]:
            columns = ", ".join(step.get("required_columns") or []) or "nessuna colonna specifica"
            lines.append(
                f"- Step {step.get('priority')}: {step.get('analysis_type')} "
                f"su {columns}. {step.get('rationale', '')}"
            )
        questions = strategy.get("clarification_questions") or []
        if questions:
            lines.append(
                "- Chiarimenti aperti: "
                + "; ".join(item.get("question", "") for item in questions[:3])
            )
        excluded = strategy.get("excluded_analyses") or []
        if excluded:
            lines.append(
                "- Analisi escluse: "
                + "; ".join(
                    f"{item.get('analysis_type')} ({item.get('reason')})"
                    for item in excluded[:3]
                )
                )
        return "\n".join(lines)

    def _format_domain_pack_context(self, context: dict[str, Any]) -> str:
        if not isinstance(context, dict) or context.get("status") != "detected":
            return "- Nessun domain pack riconosciuto con confidenza sufficiente."

        suggestion = context.get("suggestion") if isinstance(context.get("suggestion"), dict) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), dict) else {}
        manifest = knowledge.get("manifest") if isinstance(knowledge.get("manifest"), dict) else {}
        lines = [
            f"- Pack: {manifest.get('name', context.get('pack_id', 'n/a'))}",
            f"- Confidence: {self._fmt(suggestion.get('confidence_score', 0))}",
        ]
        if suggestion.get("reason"):
            lines.append(f"- Motivo: {suggestion['reason']}")
        kpis = [
            item.get("name")
            for item in knowledge.get("kpi_definitions", [])[:8]
            if isinstance(item, dict) and item.get("name")
        ]
        if kpis:
            lines.append("- KPI di dominio: " + ", ".join(kpis))
        rules = [
            item.get("description")
            for item in knowledge.get("strategy_rules", [])[:5]
            if isinstance(item, dict) and item.get("description")
        ]
        if rules:
            lines.append("- Regole applicate: " + "; ".join(rules))
        return "\n".join(lines)

    def _format_advanced_statistics(
        self,
        results: dict[str, Any],
        forbidden_columns: list[str] | None = None,
    ) -> str:
        if not isinstance(results, dict) or not results:
            return "- Statistiche avanzate non disponibili."
        if results.get("status") == "skipped":
            return f"- Analisi statistica avanzata non eseguita: {results.get('reason', 'non richiesta')}."
        if results.get("status") == "empty":
            return "- Dataset vuoto: statistiche avanzate non calcolabili."
        lines: list[str] = []
        forbidden = set(forbidden_columns or [])
        numeric_analysis = results.get("numeric_analysis") or {}
        for column, analysis in numeric_analysis.items():
            if column in forbidden:
                continue
            if not self._is_business_metric(column, None):
                continue
            if not isinstance(analysis, dict) or analysis.get("status") != "computed":
                continue
            percentiles = analysis.get("percentiles") or {}
            dispersion = analysis.get("dispersion") or {}
            outliers = analysis.get("outliers") or {}
            iqr_outliers = (outliers.get("iqr") or {}).get("outlier_count", 0)
            zscore_outliers = (outliers.get("zscore") or {}).get("outlier_count", 0)
            modified_outliers = (outliers.get("modified_zscore") or {}).get(
                "outlier_count",
                0,
            )
            lines.append(
                f"- **{column}:** P50 {self._fmt(percentiles.get('p50'))}, "
                f"P90 {self._fmt(percentiles.get('p90'))}, "
                f"P95 {self._fmt(percentiles.get('p95'))}, "
                f"IQR {self._fmt(dispersion.get('iqr'))}, "
                f"MAD {self._fmt(dispersion.get('mad'))}; "
                f"outlier IQR/Z/modZ: {iqr_outliers}/{zscore_outliers}/{modified_outliers}."
            )
            if len(lines) >= 5:
                break
        threshold_results = results.get("threshold_comparisons") or {}
        for key, item in list(threshold_results.items())[:3]:
            if isinstance(item, dict) and item.get("status") == "computed":
                lines.append(
                    f"- **Soglia {key}:** breach rate {self._fmt(item.get('breach_rate'))}% "
                    f"su {item.get('valid_count', 0)} valori validi."
                )
        correlations = results.get("correlation_matrices") or {}
        pearson = correlations.get("pearson") or {}
        top_pairs = pearson.get("top_pairs") or []
        valid_pairs = [
            pair for pair in top_pairs
            if all(column not in forbidden and self._is_business_metric(column, None) for column in pair.get("columns", []))
        ]
        if valid_pairs:
            best = valid_pairs[0]
            pair = " / ".join(best.get("columns", []))
            lines.append(
                f"- Correlazione Pearson piu alta: {pair} = {self._fmt(best.get('correlation'))}."
            )
        missing = results.get("missing_completeness") or {}
        if missing:
            lines.append(
                f"- Completezza complessiva: {self._fmt(missing.get('overall_completeness_percent'))}%."
            )
        return "\n".join(lines) if lines else "- Nessuna statistica avanzata calcolata."

    def _format_detected_anomalies(self, results: dict[str, Any]) -> str:
        if not isinstance(results, dict) or not results:
            return "- Nessun dettaglio aggiuntivo sulle anomalie disponibile."
        if results.get("status") == "skipped":
            return f"- Controllo anomalie non eseguito: {results.get('reason', 'non richiesto')}."
        anomalies = results.get("anomalies") or []
        if not anomalies:
            return f"- Nessuna anomalia rilevata. {results.get('reason', '')}".strip()
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        ordered = sorted(
            anomalies,
            key=lambda item: (
                severity_rank.get(item.get("severity", "low"), 0),
                item.get("confidence_score", 0),
            ),
            reverse=True,
        )
        lines = []
        for item in ordered[:5]:
            evidence = item.get("evidence") or {}
            evidence_text = "; ".join(
                f"{key}: {self._fmt(value)}"
                for key, value in list(evidence.items())[:3]
            )
            lines.append(
                f"- **{item.get('severity', 'low').upper()}** "
                f"{item.get('anomaly_type')} su {item.get('affected_column')}: "
                f"osservato {self._fmt(item.get('observed_value'))}, "
                f"atteso {self._fmt(item.get('expected_value'))}, "
                f"deviazione {self._fmt(item.get('deviation'))}. "
                f"Evidenza: {evidence_text or item.get('method')}. "
                f"Raccomandazione: {item.get('recommendation')}"
            )
        return "\n".join(lines)

    def _format_root_causes(self, results: dict[str, Any]) -> str:
        if not isinstance(results, dict) or not results:
            return "- Root cause analysis locale non disponibile."
        if results.get("status") in {"skipped", "insufficient_evidence"}:
            reason = results.get("reason") or "evidenze insufficienti"
            return f"- Root cause analysis non conclusiva: {reason}."
        causes = results.get("possible_causes") or []
        if not causes:
            return "- Nessuna causa radice supportata da evidenze disponibili."
        lines = []
        for cause in causes[:5]:
            if not isinstance(cause, dict):
                continue
            metrics = ", ".join(cause.get("affected_metrics") or []) or "metriche non specificate"
            evidence_count = len(cause.get("supporting_evidence") or [])
            alternatives = "; ".join((cause.get("alternative_explanations") or [])[:2])
            actions = "; ".join((cause.get("recommended_actions") or [])[:2])
            lines.append(
                f"- **{cause.get('severity', 'low').upper()}** "
                f"{cause.get('title', 'Causa possibile')} "
                f"(confidence {self._fmt(cause.get('confidence_score', 0))}) "
                f"su {metrics}. Evidenze: {evidence_count}. "
                f"Alternative: {alternatives or 'non disponibili'}. "
                f"Azioni: {actions or 'validare con owner del processo'}."
            )
        return "\n".join(lines)

    def _fmt(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(value)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

    def _is_business_metric(
        self,
        column: str,
        semantic_columns: dict[str, dict[str, Any]] | None,
    ) -> bool:
        if str(column).upper() == "TEMPO_ATTIVAZIONE_GIORNI":
            return True
        if not semantic_columns:
            normalized = str(column).lower().replace("_", "")
            return not any(
                term in normalized
                for term in ("id", "pyid", "contrattoid", "idcontrattotlm", "serialnumber")
            )
        semantic_type = (semantic_columns.get(str(column)) or {}).get("semantic_type")
        return semantic_type in {"METRIC", "AMOUNT", "PERCENTAGE", "DURATION"}

    def _is_useful_segment_column(
        self,
        column: Any,
        segment: dict[str, Any] | None = None,
    ) -> bool:
        normalized = str(column or "").lower().replace("_", "")
        if not normalized:
            return False
        blocked_terms = {
            "pyid",
            "contrattoid",
            "serialnumber",
            "idcontrattotlm",
        }
        if normalized in blocked_terms or any(term in normalized for term in blocked_terms):
            return False
        values = (segment or {}).get("segments") or []
        if len(values) <= 1:
            return False
        total = sum(float(item.get("value", 0) or 0) for item in values if isinstance(item, dict))
        if total:
            leader = max(
                (item for item in values if isinstance(item, dict)),
                key=lambda item: float(item.get("value", 0) or 0),
                default=None,
            )
            if leader and float(leader.get("value", 0) or 0) / total >= 0.95:
                return False
        share = (segment or {}).get("leading_share_percent")
        if self._is_number(share) and float(share) >= 95:
            return False
        return True

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
