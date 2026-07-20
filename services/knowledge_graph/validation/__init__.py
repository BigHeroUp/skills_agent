"""Read-only structural validation for raw Knowledge Graph documents."""

from .reader import RawGraphDocumentReader
from .report import GraphQualityReport, QualityStatus
from .service import validate_graph
from .validator import GraphValidationResult, GraphValidator

__all__ = [
    "GraphQualityReport",
    "GraphValidationResult",
    "GraphValidator",
    "QualityStatus",
    "RawGraphDocumentReader",
    "validate_graph",
]
