"""Reproducible, domain-neutral functional benchmark for the deterministic engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from services.analysis_engine import AnalysisEngine


@dataclass(frozen=True)
class DomainFixture:
    domain: str
    dimension: str
    metric: str
    labels: tuple[str, str, str]

    def records(self) -> list[dict[str, Any]]:
        first, second, third = self.labels
        return [
            {self.dimension: first, "canale": "web", self.metric: 10.0},
            {self.dimension: first, "canale": "web", self.metric: 10.0},
            {self.dimension: second, "canale": "app", self.metric: 25.0},
            {self.dimension: third, "canale": "web", self.metric: 5.0},
            {self.dimension: second, "canale": "store", self.metric: None},
        ]


FIXTURES = (
    DomainFixture("retail", "categoria", "ricavo", ("Casa", "Sport", "Libri")),
    DomainFixture("energia", "fascia", "consumo", ("Giorno", "Sera", "Notte")),
    DomainFixture("allenamento", "disciplina", "distanza", ("Corsa", "Nuoto", "Bici")),
    DomainFixture("supporto", "priorita", "durata", ("Alta", "Media", "Bassa")),
    DomainFixture("universita", "corso", "crediti", ("Storia", "Fisica", "Arte")),
    DomainFixture("meteo", "stazione", "temperatura", ("Nord", "Centro", "Sud")),
)


def benchmark_cases() -> list[dict[str, Any]]:
    """Return 30 independently specified intent/result contracts across six domains."""
    cases: list[dict[str, Any]] = []
    for fixture in FIXTURES:
        first, second, third = fixture.labels
        common = {"domain": fixture.domain, "records": fixture.records()}
        cases.extend([
            {
                **common,
                "id": f"{fixture.domain}-count",
                "prompt": f"Conta gli elementi per {fixture.dimension}",
                "expected_type": "count_occurrences",
                "expected": {
                    "target_column": fixture.dimension,
                    "total_records": 5,
                    "counts": [
                        {"value": first, "count": 2},
                        {"value": second, "count": 2},
                        {"value": third, "count": 1},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-sum",
                "prompt": f"Calcola la somma di {fixture.metric} per {fixture.dimension}",
                "expected_type": "numeric_aggregation",
                "expected": {
                    "aggregation": "sum",
                    "group_by_column": fixture.dimension,
                    "value_column": fixture.metric,
                    "groups": [
                        {"group": second, "value": 25.0},
                        {"group": first, "value": 20.0},
                        {"group": third, "value": 5.0},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-top",
                "prompt": f"Top 2 {fixture.dimension} per somma di {fixture.metric}",
                "expected_type": "top_n",
                "expected": {
                    "aggregation": "sum",
                    "target_column": fixture.dimension,
                    "value_column": fixture.metric,
                    "top": [
                        {"value": second, "metric": 25.0},
                        {"value": first, "metric": 20.0},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-nulls",
                "prompt": "Trova tutti i valori mancanti",
                "expected_type": "null_detection",
                "expected": {
                    "row_count": 5,
                    "total_nulls": 1,
                    "columns_with_nulls": [
                        {"column": fixture.metric, "null_count": 1, "null_percent": 20.0}
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-duplicates",
                "prompt": "Individua le righe duplicate",
                "expected_type": "duplicate_detection",
                "expected": {
                    "row_count": 5,
                    "duplicate_rows": 1,
                    "duplicate_groups_rows": 2,
                },
            },
        ])
    return cases


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _contains(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def run_functional_benchmark() -> dict[str, Any]:
    engine = AnalysisEngine()
    results = []
    for case in benchmark_cases():
        payload = engine.run(case["prompt"], pd.DataFrame(case["records"]), source_type="benchmark")
        actual = payload["deterministic_results"]
        inferred_type = payload["analysis_plan"]["analysis_type"]
        passed = inferred_type == case["expected_type"] and _contains(actual, case["expected"])
        results.append({
            "id": case["id"],
            "domain": case["domain"],
            "passed": passed,
            "expected_type": case["expected_type"],
            "actual_type": inferred_type,
        })
    passed = sum(item["passed"] for item in results)
    domains = len({item["domain"] for item in results})
    return {
        "status": "passed" if passed == len(results) else "failed",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "domains": domains,
        "results": results,
    }
