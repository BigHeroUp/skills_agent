"""Motore locale per rilevare anomalie statistiche e degrado operativo."""

from __future__ import annotations

import hashlib
import json
import math
import operator as operator_module
from typing import Any

import numpy as np
import pandas as pd

from services.advanced_statistical_engine import AdvancedStatisticalEngine


class AnomalyDetectionEngine:
    """Rileva anomalie spiegabili senza chiamate OpenAI."""

    SCHEMA_VERSION = 1
    SEVERITIES = ("low", "medium", "high", "critical")

    def __init__(self, statistical_engine: AdvancedStatisticalEngine | None = None):
        self._stats = statistical_engine or AdvancedStatisticalEngine()

    def detect_anomalies(self, df, config: dict | None = None) -> dict:
        """Esegue rilevazione complessiva su numeriche, trend e SLA."""
        cfg = config if isinstance(config, dict) else {}
        if not isinstance(df, pd.DataFrame) or df.empty:
            return self._result(
                status="empty",
                anomalies=[],
                signals=[],
                reason="Dataframe vuoto: nessuna evidenza sufficiente per rilevare anomalie.",
            )

        numeric = [str(column) for column in df.select_dtypes(include="number").columns]
        datetime_columns = self._datetime_columns(df)
        signals = []
        anomalies = []

        numeric_results = self.detect_numeric_anomalies(
            df,
            columns=cfg.get("numeric_columns") or numeric,
            config=cfg,
        )
        signals.append(numeric_results)
        anomalies.extend(numeric_results.get("anomalies", []))

        time_column = cfg.get("time_column") or (datetime_columns[0] if datetime_columns else None)
        value_column = cfg.get("value_column") or self._preferred_numeric_column(numeric)
        if time_column:
            time_results = self.detect_time_series_anomalies(
                df,
                time_column=time_column,
                value_column=value_column,
                config=cfg,
            )
            signals.append(time_results)
            anomalies.extend(time_results.get("anomalies", []))
            if value_column:
                degradation = self.detect_degradation(
                    df,
                    time_column=time_column,
                    value_column=value_column,
                    config=cfg,
                )
                signals.append(degradation)
                anomalies.extend(degradation.get("anomalies", []))

        threshold_config = cfg.get("sla") or cfg.get("threshold")
        if isinstance(threshold_config, dict):
            column = threshold_config.get("column") or value_column
            threshold = threshold_config.get("threshold")
            if column is not None and threshold is not None:
                sla = self.detect_sla_violations(
                    df,
                    column=column,
                    threshold=threshold,
                    operator=threshold_config.get("operator", "<="),
                    config=cfg,
                )
                signals.append(sla)
                anomalies.extend(sla.get("anomalies", []))

        anomalies = self._deduplicate_anomalies(anomalies)
        return self._result(
            status="computed",
            anomalies=anomalies,
            signals=signals,
            reason=(
                None
                if anomalies
                else "Nessuna anomalia rilevata con le soglie e i metodi configurati."
            ),
        )

    def detect_numeric_anomalies(
        self,
        df,
        columns: list[str] | None = None,
        config: dict | None = None,
    ) -> dict:
        """Rileva outlier numerici usando AdvancedStatisticalEngine."""
        cfg = config if isinstance(config, dict) else {}
        if not isinstance(df, pd.DataFrame) or df.empty:
            return self._result(
                status="empty",
                anomalies=[],
                signals=[],
                reason="Dataframe vuoto.",
                detector="numeric",
            )
        available = [str(column) for column in df.select_dtypes(include="number").columns]
        selected = [column for column in (columns or available) if column in df.columns and column in available]
        if not selected:
            return self._result(
                status="no_numeric_columns",
                anomalies=[],
                signals=[],
                reason="Nessuna colonna numerica disponibile per outlier detection.",
                detector="numeric",
            )

        methods = cfg.get("outlier_methods", ["iqr", "zscore", "modified_zscore"])
        anomalies = []
        signals = []
        for column in selected:
            analysis = self._stats.analyze_numeric_column(
                df,
                column,
                {"outlier_methods": methods},
            )
            signals.append({"column": column, "analysis": analysis})
            if analysis.get("status") != "computed":
                continue
            for method, outlier_result in (analysis.get("outliers") or {}).items():
                if outlier_result.get("status") != "computed":
                    continue
                for value, index in zip(
                    outlier_result.get("outlier_values", []),
                    outlier_result.get("outlier_indices", []),
                ):
                    severity = self._severity_from_ratio(
                        self._numeric_deviation_ratio(
                            observed=value,
                            expected=analysis.get("descriptive_statistics", {}).get("median"),
                            fallback=analysis.get("dispersion", {}).get("iqr"),
                        )
                    )
                    anomalies.append(self._anomaly(
                        anomaly_type="numeric_outlier",
                        severity=severity,
                        confidence_score=self._confidence_for_severity(severity),
                        affected_column=column,
                        observed_value=value,
                        expected_value=analysis.get("descriptive_statistics", {}).get("median"),
                        deviation=self._round(
                            float(value) - float(analysis.get("descriptive_statistics", {}).get("median", 0))
                        ),
                        evidence={
                            "row_index": index,
                            "method_details": outlier_result.get("details", {}),
                            "outlier_percent": outlier_result.get("outlier_percent"),
                        },
                        recommendation=(
                            f"Verificare il record {index} di {column}: distinguere errore dati, evento reale "
                            "o caso operativo da gestire separatamente."
                        ),
                        method=method,
                    ))
        return self._result(
            status="computed",
            anomalies=anomalies,
            signals=signals,
            reason=None if anomalies else "Nessun outlier numerico rilevato.",
            detector="numeric",
        )

    def detect_time_series_anomalies(
        self,
        df,
        time_column: str,
        value_column: str | None = None,
        config: dict | None = None,
    ) -> dict:
        """Rileva spike e cambi improvvisi su serie temporali aggregate."""
        cfg = config if isinstance(config, dict) else {}
        if not self._valid_column(df, time_column):
            return self._result(
                status="missing_column",
                anomalies=[],
                signals=[],
                reason=f"Colonna temporale non disponibile: {time_column}.",
                detector="time_series",
            )
        trend = self._stats.analyze_trend(
            df,
            time_column,
            value_column,
            {
                "frequency": cfg.get("frequency", "MS"),
                "rolling_window": cfg.get("rolling_window", 3),
                "aggregation": cfg.get("aggregation", "mean"),
            },
        )
        if trend.get("status") != "computed":
            return self._result(
                status=trend.get("status", "not_computable"),
                anomalies=[],
                signals=[trend],
                reason="Serie temporale non calcolabile con i dati disponibili.",
                detector="time_series",
            )

        spike_std_multiplier = float(cfg.get("spike_std_multiplier", 2.0))
        growth_threshold = float(cfg.get("growth_threshold_percent", 50.0))
        anomalies = []
        for point in trend.get("points", []):
            value = point.get("value")
            rolling_mean = point.get("rolling_mean")
            rolling_std = point.get("rolling_std")
            growth = point.get("growth_percent")
            if self._is_number(value) and self._is_number(rolling_mean) and self._is_number(rolling_std):
                expected = float(rolling_mean)
                std = float(rolling_std)
                if std > 0 and float(value) > expected + spike_std_multiplier * std:
                    deviation = float(value) - expected
                    severity = self._severity_from_ratio(deviation / std)
                    anomalies.append(self._anomaly(
                        anomaly_type="time_series_spike",
                        severity=severity,
                        confidence_score=self._confidence_for_severity(severity),
                        affected_column=value_column or "__row_count__",
                        affected_period=point.get("period"),
                        observed_value=value,
                        expected_value=self._round(expected),
                        deviation=self._round(deviation),
                        evidence={
                            "rolling_std": rolling_std,
                            "spike_std_multiplier": spike_std_multiplier,
                            "growth_percent": growth,
                        },
                        recommendation="Verificare cause operative del picco e confrontare con capacita, backlog o eventi esterni.",
                        method="rolling_mean_std",
                    ))
            if self._is_number(growth) and abs(float(growth)) >= growth_threshold:
                severity = self._severity_from_ratio(abs(float(growth)) / growth_threshold)
                anomalies.append(self._anomaly(
                    anomaly_type="sudden_change",
                    severity=severity,
                    confidence_score=self._confidence_for_severity(severity),
                    affected_column=value_column or "__row_count__",
                    affected_period=point.get("period"),
                    observed_value=value,
                    expected_value=rolling_mean,
                    deviation=growth,
                    evidence={
                        "growth_percent": growth,
                        "growth_threshold_percent": growth_threshold,
                    },
                    recommendation="Analizzare il cambio improvviso rispetto al periodo precedente e validare eventuali cambi di processo.",
                    method="period_over_period_growth",
                ))
        return self._result(
            status="computed",
            anomalies=self._deduplicate_anomalies(anomalies),
            signals=[trend],
            reason=None if anomalies else "Nessuno spike temporale o cambio improvviso rilevato.",
            detector="time_series",
        )

    def detect_degradation(
        self,
        df,
        time_column: str,
        value_column: str,
        config: dict | None = None,
    ) -> dict:
        """Rileva degrado confrontando finestre recenti e baseline storica."""
        cfg = config if isinstance(config, dict) else {}
        if not self._valid_column(df, time_column) or not self._valid_column(df, value_column):
            return self._result(
                status="missing_column",
                anomalies=[],
                signals=[],
                reason="Colonna temporale o metrica di degrado non disponibile.",
                detector="degradation",
            )
        data = df[[time_column, value_column]].copy()
        data["_time"] = pd.to_datetime(data[time_column], errors="coerce")
        data["_value"] = pd.to_numeric(data[value_column], errors="coerce")
        data = data.dropna(subset=["_time", "_value"]).sort_values("_time")
        min_points = int(cfg.get("degradation_min_points", 6))
        if len(data) < min_points:
            return self._result(
                status="insufficient_data",
                anomalies=[],
                signals=[],
                reason=f"Servono almeno {min_points} punti validi per stimare degrado.",
                detector="degradation",
            )
        window = max(1, int(cfg.get("degradation_window", max(2, len(data) // 3))))
        threshold = float(cfg.get("degradation_threshold_percent", 20.0))
        higher_is_worse = bool(cfg.get("higher_is_worse", True))
        baseline = data.iloc[:-window]["_value"]
        recent = data.iloc[-window:]["_value"]
        if baseline.empty or recent.empty:
            return self._result(
                status="insufficient_data",
                anomalies=[],
                signals=[],
                reason="Baseline o finestra recente non disponibili.",
                detector="degradation",
            )
        baseline_mean = float(baseline.mean())
        recent_mean = float(recent.mean())
        if baseline_mean == 0:
            change_percent = None
            degraded = False
        else:
            change_percent = (recent_mean - baseline_mean) / abs(baseline_mean) * 100
            degraded = (
                change_percent >= threshold
                if higher_is_worse
                else change_percent <= -threshold
            )
        anomalies = []
        if degraded:
            ratio = abs(float(change_percent)) / threshold if change_percent is not None else 1.0
            severity = self._severity_from_ratio(ratio)
            anomalies.append(self._anomaly(
                anomaly_type="performance_degradation",
                severity=severity,
                confidence_score=self._confidence_for_severity(severity),
                affected_column=value_column,
                affected_period={
                    "from": data.iloc[-window:]["_time"].min().isoformat(),
                    "to": data.iloc[-window:]["_time"].max().isoformat(),
                },
                observed_value=self._round(recent_mean),
                expected_value=self._round(baseline_mean),
                deviation=self._round(change_percent),
                evidence={
                    "baseline_mean": self._round(baseline_mean),
                    "recent_mean": self._round(recent_mean),
                    "threshold_percent": threshold,
                    "recent_window": window,
                    "higher_is_worse": higher_is_worse,
                },
                recommendation="Indagare le cause del degrado recente e confrontare con volumi, capacita e cambi applicativi.",
                method="recent_window_vs_baseline_mean",
            ))
        return self._result(
            status="computed",
            anomalies=anomalies,
            signals=[{
                "baseline_mean": self._round(baseline_mean),
                "recent_mean": self._round(recent_mean),
                "change_percent": self._round(change_percent),
            }],
            reason=None if anomalies else "Nessun degrado prestazionale oltre soglia rilevato.",
            detector="degradation",
        )

    def compare_against_baseline(
        self,
        current_results: dict,
        baseline_results: dict,
        config: dict | None = None,
    ) -> dict:
        """Confronta risultati statistici correnti contro baseline storica."""
        cfg = config if isinstance(config, dict) else {}
        threshold = float(cfg.get("drift_threshold_percent", 20.0))
        current_numeric = (current_results or {}).get("numeric_analysis") or {}
        baseline_numeric = (baseline_results or {}).get("numeric_analysis") or {}
        anomalies = []
        signals = []
        for column, current in current_numeric.items():
            baseline = baseline_numeric.get(column)
            if not isinstance(current, dict) or not isinstance(baseline, dict):
                continue
            current_mean = (current.get("descriptive_statistics") or {}).get("mean")
            baseline_mean = (baseline.get("descriptive_statistics") or {}).get("mean")
            if not self._is_number(current_mean) or not self._is_number(baseline_mean) or float(baseline_mean) == 0:
                continue
            change = (float(current_mean) - float(baseline_mean)) / abs(float(baseline_mean)) * 100
            signals.append({
                "column": column,
                "current_mean": self._round(current_mean),
                "baseline_mean": self._round(baseline_mean),
                "change_percent": self._round(change),
            })
            if abs(change) >= threshold:
                severity = self._severity_from_ratio(abs(change) / threshold)
                anomalies.append(self._anomaly(
                    anomaly_type="baseline_drift",
                    severity=severity,
                    confidence_score=self._confidence_for_severity(severity),
                    affected_column=column,
                    observed_value=self._round(current_mean),
                    expected_value=self._round(baseline_mean),
                    deviation=self._round(change),
                    evidence={
                        "drift_threshold_percent": threshold,
                        "current_mean": self._round(current_mean),
                        "baseline_mean": self._round(baseline_mean),
                    },
                    recommendation="Validare se il drift e atteso, dovuto a cambio popolazione dati o a degrado del processo.",
                    method="mean_drift_vs_baseline",
                ))
        return self._result(
            status="computed",
            anomalies=anomalies,
            signals=signals,
            reason=None if anomalies else "Nessun drift rispetto alla baseline oltre soglia.",
            detector="baseline",
        )

    def detect_sla_violations(
        self,
        df,
        column: str,
        threshold: float,
        operator: str = "<=",
        config: dict | None = None,
    ) -> dict:
        """Rileva possibili violazioni SLA/soglia su una colonna numerica."""
        cfg = config if isinstance(config, dict) else {}
        comparison = self._stats.compare_threshold(df, column, threshold, operator=operator)
        if comparison.get("status") != "computed":
            return self._result(
                status=comparison.get("status", "not_computable"),
                anomalies=[],
                signals=[comparison],
                reason="Confronto soglia non calcolabile con i dati disponibili.",
                detector="sla",
            )
        breach_rate = float(comparison.get("breach_rate", 0) or 0)
        min_breach_rate = float(cfg.get("sla_min_breach_rate", 0.0))
        anomalies = []
        if comparison.get("breach_count", 0) > 0 and breach_rate >= min_breach_rate:
            severity = self._severity_from_rate(breach_rate)
            anomalies.append(self._anomaly(
                anomaly_type="sla_violation",
                severity=severity,
                confidence_score=self._confidence_for_severity(severity),
                affected_column=column,
                observed_value=breach_rate,
                expected_value=0.0,
                deviation=breach_rate,
                evidence={
                    "threshold": comparison.get("threshold"),
                    "operator": comparison.get("operator"),
                    "breach_count": comparison.get("breach_count"),
                    "valid_count": comparison.get("valid_count"),
                    "breach_indices": comparison.get("breach_indices", [])[:20],
                },
                recommendation="Analizzare i record fuori soglia e verificare impatto SLA, priorita e cause operative.",
                method="threshold_comparison",
            ))
        return self._result(
            status="computed",
            anomalies=anomalies,
            signals=[comparison],
            reason=None if anomalies else "Nessuna violazione SLA/soglia rilevata.",
            detector="sla",
        )

    def export_anomaly_summary(self, results: dict) -> dict:
        """Esporta una sintesi JSON-safe delle anomalie rilevate."""
        data = results if isinstance(results, dict) else {}
        anomalies = data.get("anomalies") or []
        severity_counts = {severity: 0 for severity in self.SEVERITIES}
        type_counts: dict[str, int] = {}
        for item in anomalies:
            severity = item.get("severity", "low")
            if severity in severity_counts:
                severity_counts[severity] += 1
            anomaly_type = str(item.get("anomaly_type", "unknown"))
            type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": data.get("status", "unknown"),
            "anomaly_count": len(anomalies),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "top_anomalies": sorted(
                anomalies,
                key=lambda item: (
                    self.SEVERITIES.index(item.get("severity", "low"))
                    if item.get("severity", "low") in self.SEVERITIES
                    else 0,
                    item.get("confidence_score", 0),
                ),
                reverse=True,
            )[:10],
            "reason": data.get("reason"),
        })

    def _result(
        self,
        status: str,
        anomalies: list[dict],
        signals: list[Any],
        reason: str | None,
        detector: str = "global",
    ) -> dict:
        return self._json_safe({
            "schema_version": self.SCHEMA_VERSION,
            "status": status,
            "detector": detector,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "signals": signals,
            "reason": reason,
        })

    def _anomaly(
        self,
        anomaly_type: str,
        severity: str,
        confidence_score: float,
        affected_column: str,
        observed_value: Any,
        expected_value: Any,
        deviation: Any,
        evidence: dict,
        recommendation: str,
        method: str,
        affected_period: Any = None,
    ) -> dict:
        payload = {
            "anomaly_type": anomaly_type,
            "severity": severity if severity in self.SEVERITIES else "low",
            "confidence_score": self._round(confidence_score),
            "affected_column": str(affected_column),
            "affected_period": affected_period,
            "observed_value": self._json_safe(observed_value),
            "expected_value": self._json_safe(expected_value),
            "deviation": self._json_safe(deviation),
            "evidence": evidence,
            "recommendation": recommendation,
            "method": method,
        }
        payload["anomaly_id"] = self._anomaly_id(payload)
        return self._json_safe(payload)

    def _anomaly_id(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return "anomaly-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def _deduplicate_anomalies(self, anomalies: list[dict]) -> list[dict]:
        output = []
        positions = {}
        for item in anomalies:
            key = (
                item.get("anomaly_type"),
                item.get("affected_column"),
                json.dumps(item.get("affected_period"), sort_keys=True, default=str),
                json.dumps(item.get("observed_value"), sort_keys=True, default=str),
                json.dumps((item.get("evidence") or {}).get("row_index"), sort_keys=True, default=str),
            )
            if key in positions:
                existing = output[positions[key]]
                methods = list(existing.get("detection_methods") or [existing.get("method")])
                if item.get("method") not in methods:
                    methods.append(item.get("method"))
                existing["detection_methods"] = [method for method in methods if method]
                existing["detection_count"] = len(existing["detection_methods"])
                if float(item.get("confidence_score") or 0) > float(existing.get("confidence_score") or 0):
                    existing["confidence_score"] = item.get("confidence_score")
                    existing["severity"] = item.get("severity")
                continue
            item = dict(item)
            item["detection_methods"] = [item.get("method")] if item.get("method") else []
            item["detection_count"] = len(item["detection_methods"])
            positions[key] = len(output)
            output.append(item)
        return output

    def _datetime_columns(self, df: pd.DataFrame) -> list[str]:
        output = [str(column) for column in df.select_dtypes(include=["datetime", "datetimetz"]).columns]
        for column in df.columns:
            if str(column) in output:
                continue
            name = str(column).lower()
            if "date" not in name and "time" not in name:
                continue
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().any():
                output.append(str(column))
        return output

    def _preferred_numeric_column(self, numeric_columns: list[str]) -> str | None:
        if not numeric_columns:
            return None
        terms = ("duration", "durata", "tempo", "time", "latency", "latenza", "sla", "hours", "minuti")
        for column in numeric_columns:
            normalized = str(column).lower()
            if any(term in normalized for term in terms):
                return column
        return numeric_columns[0]

    def _valid_column(self, df, column: str) -> bool:
        return isinstance(df, pd.DataFrame) and column in df.columns

    def _numeric_deviation_ratio(self, observed: Any, expected: Any, fallback: Any) -> float:
        if not self._is_number(observed) or not self._is_number(expected):
            return 1.0
        denominator = abs(float(fallback)) if self._is_number(fallback) and float(fallback) != 0 else abs(float(expected))
        if denominator == 0:
            return 1.0
        return abs(float(observed) - float(expected)) / denominator

    def _severity_from_ratio(self, ratio: float | None) -> str:
        if ratio is None or not math.isfinite(float(ratio)):
            return "low"
        value = abs(float(ratio))
        if value >= 4:
            return "critical"
        if value >= 2.5:
            return "high"
        if value >= 1.25:
            return "medium"
        return "low"

    def _severity_from_rate(self, rate: float) -> str:
        if rate >= 50:
            return "critical"
        if rate >= 25:
            return "high"
        if rate >= 10:
            return "medium"
        return "low"

    def _confidence_for_severity(self, severity: str) -> float:
        return {
            "low": 0.55,
            "medium": 0.68,
            "high": 0.82,
            "critical": 0.92,
        }.get(severity, 0.5)

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool) and math.isfinite(float(value))

    def _round(self, value: Any, digits: int = 4) -> Any:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return self._json_safe(value)
        if not math.isfinite(number):
            return None
        return round(number, digits)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return self._round(float(value))
        if isinstance(value, (pd.Timestamp,)):
            return value.isoformat()
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        json.dumps(value, ensure_ascii=False, default=str)
        return value
