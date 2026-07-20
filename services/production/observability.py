"""Structured in-process telemetry for Product Intelligence stages."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from utils.logging_config import get_logger


logger = get_logger("product_flow")


class ProductFlowTimeout(RuntimeError):
    pass


@dataclass(frozen=True)
class StageMetric:
    stage: str
    status: str
    duration_ms: float
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "stage": self.stage,
            "status": self.status,
        }


class ProductFlowTelemetry:
    def __init__(
        self,
        run_id: str,
        *,
        stage_timeout_seconds: float,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.run_id = run_id
        self.stage_timeout_seconds = stage_timeout_seconds
        self.clock = clock
        self.metrics: list[StageMetric] = []

    def run(self, stage: str, operation):
        started = self.clock()
        try:
            result = operation()
        except Exception as exc:
            self._record(stage, "error", started, type(exc).__name__)
            raise
        elapsed = self.clock() - started
        if elapsed > self.stage_timeout_seconds:
            self._record(stage, "timeout", started, "ProductFlowTimeout")
            raise ProductFlowTimeout(
                f"stage {stage} exceeded {self.stage_timeout_seconds}s soft deadline"
            )
        self._record(stage, "completed", started, None)
        return result

    def _record(self, stage, status, started, error_type):
        metric = StageMetric(
            stage=stage,
            status=status,
            duration_ms=round((self.clock() - started) * 1000, 3),
            error_type=error_type,
        )
        self.metrics.append(metric)
        logger.info("product_flow_stage %s", json.dumps({
            "run_id": self.run_id,
            **metric.to_dict(),
        }, sort_keys=True))

    def to_dict(self) -> dict[str, Any]:
        durations = [item.duration_ms for item in self.metrics]
        return {
            "run_id": self.run_id,
            "stage_count": len(self.metrics),
            "stages": [item.to_dict() for item in self.metrics],
            "total_duration_ms": round(sum(durations), 3),
        }
