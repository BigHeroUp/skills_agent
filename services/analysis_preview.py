"""Explain the inferred semantic schema and deterministic plan before execution."""

from __future__ import annotations

import pandas as pd

from services.analysis_engine import AnalysisEngine
from services.semantic_column_classifier import SemanticColumnClassifier


def build_analysis_preview(question: str, dataframe: pd.DataFrame) -> dict:
    semantics = SemanticColumnClassifier().classify_dataframe(dataframe)
    plan = AnalysisEngine().infer_plan(question, dataframe).to_dict()
    ambiguous = [name for name, item in semantics.items() if float(item.get("confidence", 0)) < 0.7]
    return {
        "question": question,
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "analysis_plan": plan,
        "semantic_columns": semantics,
        "excluded_columns": [name for name, item in semantics.items() if item.get("semantic_type") == "IDENTIFIER"],
        "clarification_questions": [f"Confermi il significato della colonna {name}?" for name in ambiguous[:5]],
    }
