"""Deterministic private-beta readiness gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BetaGate:
    id: str
    passed: bool
    observed: Any
    required: Any
    reason: str


class BetaReadinessEvaluator:
    """Evaluate evidence without turning missing evidence into a successful gate."""

    def evaluate(self, evidence: dict[str, Any]) -> dict[str, Any]:
        cases = evidence.get("validation_cases") or {}
        feedback = evidence.get("feedback") or {}
        load = evidence.get("load_test") or {}
        operations = evidence.get("operations") or {}
        safety = evidence.get("safety") or {}
        total_feedback = int(feedback.get("total", 0) or 0)
        correct = int(feedback.get("correct", 0) or 0)
        accuracy = correct / total_feedback if total_feedback else 0.0
        gates = [
            self._gate("validation_cases", int(cases.get("total", 0) or 0) >= 30, cases.get("total", 0), ">= 30", "Serve un campione riproducibile sufficiente."),
            self._gate("domain_coverage", int(cases.get("domains", 0) or 0) >= 3, cases.get("domains", 0), ">= 3", "La beta deve coprire domini differenti."),
            self._gate("validated_accuracy", total_feedback >= 10 and accuracy >= 0.8, round(accuracy, 4), ">= 0.80 con >= 10 feedback", "La qualità deve essere misurata da feedback verificati."),
            self._gate("tenant_isolation", bool(safety.get("tenant_isolation_passed")), safety.get("tenant_isolation_passed"), True, "Nessuna risorsa deve attraversare il tenant boundary."),
            self._gate("unsupported_requests", bool(safety.get("unsupported_requests_passed")), safety.get("unsupported_requests_passed"), True, "Le richieste non supportate devono produrre astensione o errore chiaro."),
            self._gate("load_concurrency", int(load.get("concurrency", 0) or 0) >= 5 and float(load.get("error_rate", 1) if load.get("error_rate") is not None else 1) <= 0.02, {"concurrency": load.get("concurrency", 0), "error_rate": load.get("error_rate", 1)}, {"concurrency": ">= 5", "error_rate": "<= 0.02"}, "Il percorso asincrono deve reggere concorrenza controllata."),
            self._gate("backup_restore", bool(operations.get("backup_restore_passed")), operations.get("backup_restore_passed"), True, "Backup senza prova di restore non è sufficiente."),
            self._gate("retention_delete", bool(operations.get("retention_delete_passed")), operations.get("retention_delete_passed"), True, "Cancellazione e retention devono essere verificabili."),
            self._gate("monitoring", bool(operations.get("monitoring_passed")), operations.get("monitoring_passed"), True, "Stato, failure e qualità devono essere osservabili."),
            self._gate("critical_bugs", int(safety.get("open_critical_bugs", 1) or 0) == 0, safety.get("open_critical_bugs", 1), 0, "Nessun bug critico può restare aperto."),
        ]
        failed = [gate.id for gate in gates if not gate.passed]
        return {
            "status": "ready" if not failed else "not_ready",
            "passed": len(gates) - len(failed),
            "total": len(gates),
            "failed_gates": failed,
            "gates": [asdict(gate) for gate in gates],
        }

    @staticmethod
    def _gate(gate_id: str, passed: bool, observed: Any, required: Any, reason: str) -> BetaGate:
        return BetaGate(gate_id, bool(passed), observed, required, reason)
