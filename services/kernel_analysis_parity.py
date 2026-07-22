"""Shadow comparison between the production analytical engine and the Kernel."""

from __future__ import annotations

from typing import Any

import pandas as pd

from core.kernel.bootstrap import create_default_kernel
from services.analysis_engine import AnalysisEngine


class KernelAnalysisParityRunner:
    """Run both boundaries and report deterministic result parity without cutover."""

    def __init__(self, kernel=None, production_engine: AnalysisEngine | None = None) -> None:
        self.kernel = kernel or create_default_kernel()
        self.production_engine = production_engine or AnalysisEngine()

    def compare(
        self,
        question: str,
        dataframe: pd.DataFrame,
        source_type: str = "parity_check",
    ) -> dict[str, Any]:
        production = self.production_engine.run(question, dataframe, source_type=source_type)
        response = self.kernel.execute_capability(
            "analysis.categorical_count",
            payload={
                "question": question,
                "records": dataframe.to_dict(orient="records"),
                "source_type": source_type,
            },
            metadata={"shadow_mode": True},
        )
        kernel_result = response.result if response.success else {}
        fields = ("analysis_plan", "deterministic_results", "execution_summary")
        mismatches = [field for field in fields if production.get(field) != kernel_result.get(field)]
        return {
            "status": "matched" if response.success and not mismatches else "mismatched",
            "matched": bool(response.success and not mismatches),
            "mismatched_fields": mismatches,
            "kernel_errors": list(response.errors),
            "production": production,
            "kernel": kernel_result,
        }
