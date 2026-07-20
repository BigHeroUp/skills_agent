"""JSON-safe issue contracts shared by validation and quality reporting."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


_SEVERITY_RANK = {
    IssueSeverity.ERROR: 0,
    IssueSeverity.WARNING: 1,
    IssueSeverity.INFO: 2,
}


def json_safe(value: Any) -> Any:
    """Return deterministic strict-JSON-compatible data."""
    if isinstance(value, Mapping):
        return {
            str(key): json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [json_safe(item) for item in value]
        return sorted(items, key=repr) if isinstance(value, (set, frozenset)) else items
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def freeze_json(value: Any) -> Any:
    safe = json_safe(value)
    if isinstance(safe, dict):
        return MappingProxyType({key: freeze_json(item) for key, item in safe.items()})
    if isinstance(safe, list):
        return tuple(freeze_json(item) for item in safe)
    return safe


@dataclass(frozen=True)
class GraphIssue:
    """One deterministic validation finding."""

    code: str
    severity: IssueSeverity
    category: str
    location: str
    message: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
    suggestion: str = ""
    rule_id: str = ""
    rule_version: str = "1.0.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", freeze_json(dict(self.evidence or {})))

    def sort_key(self) -> tuple[Any, ...]:
        return (
            _SEVERITY_RANK[self.severity],
            self.category,
            self.code,
            self.location,
            self.rule_id,
            repr(self.evidence),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "code": self.code,
            "evidence": json_safe(self.evidence),
            "location": self.location,
            "message": self.message,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
        }
