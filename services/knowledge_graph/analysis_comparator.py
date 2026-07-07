"""Confronto deterministico tra run analitiche nel Knowledge Graph."""

from __future__ import annotations

from typing import Any


class AnalysisComparator:
    """Confronta due analysis_run usando il lineage del Knowledge Graph."""

    def __init__(self, query_engine):
        self.query_engine = query_engine

    def compare_analysis_runs(self, run_id_a: str, run_id_b: str) -> dict[str, Any]:
        """Confronta due run analitiche gia salvate nel Knowledge Graph."""
        lineage_a = self.query_engine.get_analysis_lineage(run_id_a)
        lineage_b = self.query_engine.get_analysis_lineage(run_id_b)
        run_a = lineage_a.get("analysis_run") or {}
        run_b = lineage_b.get("analysis_run") or {}
        props_a = run_a.get("properties") or {}
        props_b = run_b.get("properties") or {}

        columns_a = self._labels(lineage_a.get("columns", []))
        columns_b = self._labels(lineage_b.get("columns", []))
        anomalies_a = self._analysis_labels(lineage_a.get("anomalies", []), "affected_column")
        anomalies_b = self._analysis_labels(lineage_b.get("anomalies", []), "affected_column")
        root_causes_a = self._analysis_labels(lineage_a.get("root_causes", []), "affected_metrics")
        root_causes_b = self._analysis_labels(lineage_b.get("root_causes", []), "affected_metrics")

        return {
            "status": "computed" if run_a and run_b else "missing_analysis_run",
            "run_a": self._run_summary(run_a),
            "run_b": self._run_summary(run_b),
            "datasets": {
                "run_a": self._labels(lineage_a.get("dataset", [])),
                "run_b": self._labels(lineage_b.get("dataset", [])),
                "common": self._sorted_intersection(
                    self._labels(lineage_a.get("dataset", [])),
                    self._labels(lineage_b.get("dataset", [])),
                ),
            },
            "columns": {
                "common": self._sorted_intersection(columns_a, columns_b),
                "added": self._sorted_difference(columns_b, columns_a),
                "removed": self._sorted_difference(columns_a, columns_b),
                "run_a": sorted(columns_a),
                "run_b": sorted(columns_b),
            },
            "primary_metric": {
                "run_a": props_a.get("primary_metric"),
                "run_b": props_b.get("primary_metric"),
                "changed": props_a.get("primary_metric") != props_b.get("primary_metric"),
            },
            "time_axis": {
                "run_a": props_a.get("time_axis"),
                "run_b": props_b.get("time_axis"),
                "changed": props_a.get("time_axis") != props_b.get("time_axis"),
            },
            "insights": {
                "run_a": self._labels(lineage_a.get("insights", [])),
                "run_b": self._labels(lineage_b.get("insights", [])),
                "common": self._sorted_intersection(
                    self._labels(lineage_a.get("insights", [])),
                    self._labels(lineage_b.get("insights", [])),
                ),
                "added": self._sorted_difference(
                    self._labels(lineage_b.get("insights", [])),
                    self._labels(lineage_a.get("insights", [])),
                ),
                "removed": self._sorted_difference(
                    self._labels(lineage_a.get("insights", [])),
                    self._labels(lineage_b.get("insights", [])),
                ),
            },
            "anomalies": {
                "common": self._sorted_intersection(anomalies_a, anomalies_b),
                "new": self._sorted_difference(anomalies_b, anomalies_a),
                "resolved": self._sorted_difference(anomalies_a, anomalies_b),
                "run_a": sorted(anomalies_a),
                "run_b": sorted(anomalies_b),
            },
            "root_causes": {
                "common": self._sorted_intersection(root_causes_a, root_causes_b),
                "new": self._sorted_difference(root_causes_b, root_causes_a),
                "removed": self._sorted_difference(root_causes_a, root_causes_b),
                "run_a": sorted(root_causes_a),
                "run_b": sorted(root_causes_b),
            },
            "confidence_score": {
                "run_a": props_a.get("confidence_score"),
                "run_b": props_b.get("confidence_score"),
                "delta": self._numeric_delta(props_a.get("confidence_score"), props_b.get("confidence_score")),
            },
        }

    def summarize_comparison(self, comparison: dict[str, Any]) -> str:
        """Restituisce una sintesi italiana del confronto."""
        if comparison.get("status") != "computed":
            return "Confronto non disponibile: una o entrambe le analisi non sono presenti nel Knowledge Graph."

        columns = comparison.get("columns") or {}
        anomalies = comparison.get("anomalies") or {}
        root_causes = comparison.get("root_causes") or {}
        confidence = comparison.get("confidence_score") or {}
        metric = comparison.get("primary_metric") or {}
        time_axis = comparison.get("time_axis") or {}

        lines = [
            "Confronto deterministico tra le due analisi:",
            (
                f"- Sintesi differenze: colonne comuni {len(columns.get('common', []))}, "
                f"aggiunte {len(columns.get('added', []))}, rimosse {len(columns.get('removed', []))}."
            ),
            (
                f"- Continuita rilevate: metric primaria "
                f"{'invariata' if not metric.get('changed') else 'cambiata'} "
                f"({metric.get('run_a')} -> {metric.get('run_b')}); asse temporale "
                f"{'invariato' if not time_axis.get('changed') else 'cambiato'} "
                f"({time_axis.get('run_a')} -> {time_axis.get('run_b')})."
            ),
            f"- Nuove anomalie: {self._format_list(anomalies.get('new', []))}.",
            f"- Anomalie non piu presenti: {self._format_list(anomalies.get('resolved', []))}.",
            f"- Root cause nuove: {self._format_list(root_causes.get('new', []))}.",
            (
                f"- Confidence score: {confidence.get('run_a')} -> {confidence.get('run_b')} "
                f"(delta {confidence.get('delta')})."
            ),
            f"- Possibili evoluzioni del fenomeno: {self._evolution_note(comparison)}",
        ]
        return "\n".join(lines)

    def _run_summary(self, run: dict[str, Any]) -> dict[str, Any]:
        properties = run.get("properties") or {}
        return {
            "id": run.get("id"),
            "label": run.get("label"),
            "created_at": properties.get("created_at"),
            "source_type": properties.get("source_type"),
            "row_count": properties.get("row_count"),
            "column_count": properties.get("column_count"),
        }

    def _labels(self, nodes: list[dict[str, Any]]) -> set[str]:
        return {str(node.get("label") or node.get("id")) for node in nodes if node}

    def _analysis_labels(self, nodes: list[dict[str, Any]], property_key: str) -> set[str]:
        labels = set()
        for node in nodes or []:
            props = node.get("properties") or {}
            value = props.get(property_key)
            if isinstance(value, list):
                value = ",".join(str(item) for item in value)
            label = node.get("label") or node.get("id")
            if value:
                labels.add(f"{label}:{value}")
            elif label:
                labels.add(str(label))
        return labels

    def _sorted_intersection(self, left: set[str], right: set[str]) -> list[str]:
        return sorted(left & right)

    def _sorted_difference(self, left: set[str], right: set[str]) -> list[str]:
        return sorted(left - right)

    def _numeric_delta(self, left: Any, right: Any) -> float | None:
        try:
            return round(float(right or 0) - float(left or 0), 4)
        except (TypeError, ValueError):
            return None

    def _format_list(self, values: list[str]) -> str:
        return ", ".join(values[:5]) if values else "nessuna"

    def _evolution_note(self, comparison: dict[str, Any]) -> str:
        anomalies = comparison.get("anomalies") or {}
        confidence = comparison.get("confidence_score") or {}
        new_count = len(anomalies.get("new", []))
        resolved_count = len(anomalies.get("resolved", []))
        delta = confidence.get("delta")
        if new_count and resolved_count:
            return "il profilo anomalie e cambiato: alcuni segnali si sono risolti mentre ne emergono di nuovi."
        if new_count:
            return "emergono nuovi segnali anomali da verificare nella run piu recente."
        if resolved_count:
            return "alcuni segnali anomali non compaiono piu nella run piu recente."
        if isinstance(delta, (int, float)) and delta > 0:
            return "la struttura analitica appare stabile, con confidenza in aumento."
        if isinstance(delta, (int, float)) and delta < 0:
            return "la struttura analitica appare stabile, ma con confidenza in calo."
        return "non emergono cambiamenti sostanziali dagli elementi confrontati."


def compare_analysis_runs(query_engine, run_id_a: str, run_id_b: str) -> dict[str, Any]:
    """Wrapper funzionale per confrontare due analysis_run."""
    return AnalysisComparator(query_engine).compare_analysis_runs(run_id_a, run_id_b)


def summarize_comparison(comparison: dict[str, Any]) -> str:
    """Wrapper funzionale per sintetizzare un confronto gia calcolato."""
    return AnalysisComparator(query_engine=None).summarize_comparison(comparison)
