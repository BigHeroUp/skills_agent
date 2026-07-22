"""Kernel capability for deterministic categorical counts and cross-tabs."""

from __future__ import annotations

import pandas as pd

from core.kernel.capability import Capability, CapabilityRequest, CapabilityResponse
from services.analysis_engine import AnalysisEngine


class CategoricalCountCapability(Capability):
    """Execute the production deterministic count engine through the Kernel contract."""

    name = "analysis.categorical_count"
    version = "1.0.0"
    description = "Run deterministic categorical counts, semantic groups and cross-tabs"

    def __init__(self, engine: AnalysisEngine | None = None) -> None:
        self.engine = engine or AnalysisEngine()

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        payload = request.payload if isinstance(request.payload, dict) else {}
        question = str(payload.get("question") or "").strip()
        records = payload.get("records")
        source_type = str(payload.get("source_type") or "kernel")
        plan = payload.get("plan")

        if not question:
            return self._validation_error("Il payload deve includere 'question'.")
        if not isinstance(records, list) or not records:
            return self._validation_error("Il payload deve includere 'records' non vuoti.")
        if not all(isinstance(record, dict) for record in records):
            return self._validation_error("Ogni record deve essere un oggetto chiave-valore.")

        dataframe = pd.DataFrame.from_records(records)
        try:
            result = self.engine.run(question, dataframe, source_type=source_type, plan=plan)
        except (TypeError, ValueError) as exc:
            return CapabilityResponse(
                success=False,
                errors=[str(exc)],
                metadata={"error_type": type(exc).__name__, "row_count": int(len(dataframe))},
            )

        if result.get("analysis_plan", {}).get("analysis_type") != "count_occurrences":
            return CapabilityResponse(
                success=False,
                errors=["La capability accetta soltanto piani count_occurrences."],
                metadata={"error_type": "UnsupportedAnalysisType", "row_count": int(len(dataframe))},
            )

        return CapabilityResponse(
            success=True,
            result=result,
            metadata={
                "execution_type": "deterministic_categorical_count",
                "row_count": int(len(dataframe)),
                "source_type": source_type,
            },
        )

    def _validation_error(self, message: str) -> CapabilityResponse:
        return CapabilityResponse(
            success=False,
            errors=[message],
            metadata={"error_type": "ValidationError"},
        )
