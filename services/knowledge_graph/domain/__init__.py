"""Immutable domain contracts for lossless Knowledge Graph validation."""

from .fingerprint import GraphFingerprint
from .issues import GraphIssue, IssueSeverity
from .raw_document import (
    DuplicateJsonKey,
    NonFiniteJsonNumber,
    QuarantinedRecord,
    RawGraphDocument,
    RawReadStatus,
)

__all__ = [
    "DuplicateJsonKey",
    "GraphFingerprint",
    "GraphIssue",
    "IssueSeverity",
    "NonFiniteJsonNumber",
    "QuarantinedRecord",
    "RawGraphDocument",
    "RawReadStatus",
]
