"""Deterministic semantic consistency for the Knowledge Graph."""

from .contracts import (
    ConsistencyContext,
    ConsistencyReport,
    ConsistencyRule,
    ConsistencyStatus,
    DomainPackConsistencyRules,
)
from .rules import CORE_CONSISTENCY_RULES
from .service import evaluate_consistency

__all__ = [
    "CORE_CONSISTENCY_RULES",
    "ConsistencyContext",
    "ConsistencyReport",
    "ConsistencyRule",
    "ConsistencyStatus",
    "DomainPackConsistencyRules",
    "evaluate_consistency",
]
