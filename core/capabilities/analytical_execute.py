"""Kernel capability for the supported deterministic analysis contracts."""

from __future__ import annotations

import pandas as pd

from core.kernel.capability import Capability, CapabilityRequest, CapabilityResponse
from services.analysis_engine import AnalysisEngine


class DeterministicAnalysisCapability(Capability):
    """Execute any production-supported deterministic plan through the Kernel."""

    name = "analysis.deterministic"
    version = "1.0.0"
    description = "Run deterministic counts, aggregations, quality checks and time trends"

    def __init__(self, engine: AnalysisEngine | None = None) -> None:
        self.engine = engine or AnalysisEngine()

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        payload = request.payload if isinstance(request.payload, dict) else {}
        question = str(payload.get("question") or "").strip()
        records = payload.get("records")
        if not question:
            return self._error("Il payload deve includere 'question'.")
        if not isinstance(records, list) or not records or not all(isinstance(row, dict) for row in records):
            return self._error("Il payload deve includere 'records' non vuoti e strutturati.")
        dataframe = pd.DataFrame.from_records(records)
        try:
            result = self.engine.run(
                question,
                dataframe,
                source_type=str(payload.get("source_type") or "kernel"),
                plan=payload.get("plan"),
            )
        except (TypeError, ValueError) as exc:
            return CapabilityResponse(
                success=False,
                errors=[str(exc)],
                metadata={"error_type": type(exc).__name__, "row_count": len(dataframe)},
            )
        return CapabilityResponse(
            success=True,
            result=result,
            metadata={
                "execution_type": "deterministic_analysis",
                "analysis_type": result["analysis_plan"]["analysis_type"],
                "row_count": len(dataframe),
            },
        )

    @staticmethod
    def _error(message: str) -> CapabilityResponse:
        return CapabilityResponse(
            success=False,
            errors=[message],
            metadata={"error_type": "ValidationError"},
        )
