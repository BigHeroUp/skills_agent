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

        analysis = {
            "user_request": user_request,
            "analysis_source": "local_deterministic_engine",
            "dataset_profile": self._dataset_profile(summary, data),
            "key_findings": [],
            "kpi_summary": self._build_kpis(summary, results),
            "trend_analysis": self._build_trends(summary, results),
            "anomaly_analysis": self._build_anomalies(summary, results),
            "segmentation_analysis": self._build_segments(summary, results),
            "data_quality_notes": self._build_quality_notes(summary, results),
            "operational_recommendations": [],
            "analysis_plan": data.get("analysis_plan") or {},
            "execution_summary": data.get("execution_summary") or {},
            "detected_patterns": data.get("detected_patterns") or [],
            "knowledge_analysis_steps": data.get("knowledge_analysis_steps") or [],
            "learning_state": data.get("learning_state") or {},
            "learning_events": data.get("learning_events") or [],
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
        """Produce una sintesi direzionale basata sui soli risultati calcolati."""
        profile = analysis.get("dataset_profile", {})
        rows = profile.get("row_count", 0)
        columns = profile.get("column_count", 0)
        findings = analysis.get("key_findings", [])
        anomalies = analysis.get("anomaly_analysis", [])
        trends = analysis.get("trend_analysis", [])

        opening = (
            f"L'analisi deterministica copre {rows} righe e {columns} colonne"
            if rows or columns
            else "L'analisi deterministica disponibile non espone la dimensione completa del dataset"
        )
        sentences = [f"{opening}."]
        if findings:
            sentences.append(findings[0])
        if trends:
            sentences.append(trends[0]["summary"])
        if anomalies:
            high_priority = sum(
                item.get("severity") in {"alta", "critica"} for item in anomalies
            )
            sentences.append(
                f"Sono stati rilevati {len(anomalies)} segnali da verificare"
                + (f", di cui {high_priority} ad alta priorità." if high_priority else ".")
            )
        else:
            sentences.append("Non emergono anomalie quantificabili dai risultati disponibili.")
        return " ".join(sentences)

    def generate_final_report(self, analysis: dict) -> str:
        """Compone un report Markdown leggibile ed esportabile."""
        profile = analysis.get("dataset_profile", {})
        request = analysis.get("user_request") or "Analisi generale dei dati"
        sections = [
            "# Relazione di analisi dati",
            "",
            f"**Obiettivo:** {request}",
            (
                f"**Perimetro analizzato:** {profile.get('row_count', 0)} righe, "
                f"{profile.get('column_count', 0)} colonne."
            ),
            "",
            "## Riepilogo esecutivo",
            analysis.get("executive_summary", "Sintesi non disponibile."),
            "",
            "## Evidenze principali",
            self._bullet_list(analysis.get("key_findings", [])),
            "",
            "## KPI",
            self._format_kpis(analysis.get("kpi_summary", [])),
            "",
            "## Trend",
            self._format_structured_items(
                analysis.get("trend_analysis", []), empty="Nessun trend temporale disponibile."
            ),
            "",
            "## Segmentazione",
            self._format_structured_items(
                analysis.get("segmentation_analysis", []),
                empty="Nessuna segmentazione deterministica disponibile.",
            ),
            "",
            "## Anomalie e segnali di attenzione",
            self._format_structured_items(
                analysis.get("anomaly_analysis", []),
                empty="Nessuna anomalia quantificabile rilevata.",
            ),
            "",
            "## Qualità dei dati",
            self._bullet_list(analysis.get("data_quality_notes", [])),
            "",
            "## Raccomandazioni operative",
            self._numbered_list(analysis.get("operational_recommendations", [])),
            "",
            "## Best practice metodologiche",
            self._bullet_list(analysis.get("methodological_notes", [])),
            "",
            "## Affidabilita dei pattern",
            self._bullet_list(analysis.get("learning_reliability_notes", [])),
            "",
            "## Nota metodologica",
            (
                "Insight, KPI e conclusioni sono stati generati localmente a partire "
                "da risultati Python/Pandas già calcolati. Il report non introduce "
                "valori stimati o inventati da un modello linguistico."
            ),
        ]
        return "\n".join(sections)

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

    def _build_kpis(self, summary: dict, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kpis: list[dict[str, Any]] = []
        if summary.get("row_count") is not None:
            kpis.append(self._kpi("Righe analizzate", summary.get("row_count", 0), "volume"))
        if summary.get("column_count") is not None:
            kpis.append(self._kpi("Colonne analizzate", summary.get("column_count", 0), "struttura"))

        for column, stats in list((summary.get("numeric_summary") or {}).items())[:8]:
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

    def _build_trends(self, summary: dict, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        trends: list[dict[str, Any]] = []
        for item in results:
            result = item["result"]
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
            change_percent = None if first == 0 else round(change / abs(first) * 100, 2)
            direction = "crescente" if change > 0 else "decrescente" if change < 0 else "stabile"
            peak = max(numeric_points, key=lambda point: float(point["value"]))
            low = min(numeric_points, key=lambda point: float(point["value"]))
            summary_text = (
                f"Il trend su {result.get('time_column', 'asse temporale')} è {direction}: "
                f"da {self._fmt(first)} a {self._fmt(last)}"
                + (
                    f" ({change_percent:+.2f}%)."
                    if change_percent is not None
                    else ", con base iniziale pari a zero."
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

    def _build_anomalies(self, summary: dict, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def _build_segments(self, summary: dict, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
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
                top_values = stats.get("top_values") or {}
                if not top_values:
                    continue
                values = [{"segment": key, "value": value} for key, value in top_values.items()]
                total = sum(float(entry["value"]) for entry in values)
                leader = max(values, key=lambda entry: float(entry["value"]))
                share = round(float(leader["value"]) / total * 100, 2) if total else None
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
        if not recommendations:
            recommendations.append(
                "Confermare i KPI con i responsabili di business e impostare un monitoraggio periodico."
            )
        recommendations.append(
            "Raccogliere feedback sull'utilità dell'analisi per migliorare il riuso dei pattern analitici."
        )
        return list(dict.fromkeys(recommendations))

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
        return "\n".join(f"- {item.get('summary', str(item))}" for item in items)

    def _fmt(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(value)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

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
