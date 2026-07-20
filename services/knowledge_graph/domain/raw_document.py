"""Lossless raw Knowledge Graph document models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .fingerprint import GraphFingerprint
from .issues import GraphIssue, freeze_json, json_safe


def summarize_record(record: Any) -> dict[str, Any]:
    """Return a privacy-safe structural summary without arbitrary property values."""
    if not isinstance(record, dict) and not hasattr(record, "items"):
        return {"actual_type": type(record).__name__}
    payload = dict(record)
    summary = {
        key: json_safe(payload.get(key))
        for key in ("id", "type", "source", "target", "relationship")
        if key in payload and isinstance(payload.get(key), (str, int, float, bool, type(None)))
    }
    summary["field_names"] = sorted(str(key) for key in payload)
    properties = payload.get("properties")
    if isinstance(properties, dict) or hasattr(properties, "keys"):
        summary["property_names"] = sorted(str(key) for key in properties.keys())
    return summary


class RawReadStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    EMPTY = "empty"
    CORRUPT = "corrupt"
    NON_OBJECT = "non_object"


@dataclass(frozen=True)
class DuplicateJsonKey:
    key: str
    location: str

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "location": self.location}


@dataclass(frozen=True)
class NonFiniteJsonNumber:
    value: str
    location: str

    def to_dict(self) -> dict[str, str]:
        return {"location": self.location, "value": self.value}


@dataclass(frozen=True)
class QuarantinedRecord:
    kind: str
    location: str
    record: Any
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "record", freeze_json(self.record))
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))

    @property
    def raw_index(self) -> int | None:
        try:
            return int(self.location.rsplit("/", 1)[-1])
        except (TypeError, ValueError):
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "location": self.location,
            "raw_index": self.raw_index,
            "reason_codes": list(self.reason_codes),
            "record_summary": summarize_record(self.record),
        }


@dataclass(frozen=True)
class RawGraphDocument:
    """Raw source plus parsed data and lossless parsing findings."""

    source_name: str
    status: RawReadStatus
    original_bytes: bytes = b""
    original_text: str = ""
    fingerprint: GraphFingerprint | None = None
    root: Any = None
    parse_issues: tuple[GraphIssue, ...] = field(default_factory=tuple)
    duplicate_keys: tuple[DuplicateJsonKey, ...] = field(default_factory=tuple)
    non_finite_numbers: tuple[NonFiniteJsonNumber, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "original_bytes", bytes(self.original_bytes or b""))
        object.__setattr__(self, "root", freeze_json(self.root))
        object.__setattr__(self, "parse_issues", tuple(sorted(self.parse_issues, key=lambda item: item.sort_key())))
        object.__setattr__(
            self,
            "duplicate_keys",
            tuple(sorted(self.duplicate_keys, key=lambda item: (item.location, item.key))),
        )
        object.__setattr__(
            self,
            "non_finite_numbers",
            tuple(sorted(self.non_finite_numbers, key=lambda item: (item.location, item.value))),
        )
