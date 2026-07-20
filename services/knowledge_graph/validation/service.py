"""Application service for read-only Knowledge Graph validation."""

from __future__ import annotations

from pathlib import Path

from services.knowledge_graph.governance import (
    GOVERNANCE_POLICY_V1,
    GovernancePolicy,
    ValidationMode,
)

from .reader import RawGraphDocumentReader
from .validator import GraphValidationResult, GraphValidator


def validate_graph(
    path: str | Path,
    *,
    mode: ValidationMode | str = ValidationMode.PERMISSIVE,
    policy: GovernancePolicy = GOVERNANCE_POLICY_V1,
    reader: RawGraphDocumentReader | None = None,
    validator: GraphValidator | None = None,
) -> GraphValidationResult:
    """Read and validate a graph without creating or modifying any file."""
    resolved_mode = mode if isinstance(mode, ValidationMode) else ValidationMode(str(mode))
    document = (reader or RawGraphDocumentReader()).read(path)
    return (validator or GraphValidator()).validate(
        document,
        policy,
        mode=resolved_mode,
    )
