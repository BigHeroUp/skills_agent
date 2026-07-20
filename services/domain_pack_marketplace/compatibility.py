"""Deterministic Domain Pack compatibility checks."""

from __future__ import annotations

from typing import Any

from .contracts import PackCompatibility


def _version(value: Any) -> tuple[int, ...]:
    text = str(value or "0")
    parts = text.split(".")
    if not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid numeric version: {text}")
    return tuple(int(part) for part in parts)


def check_compatibility(
    manifest: dict[str, Any],
    *,
    platform_version: str,
    graph_schema_version: int,
) -> PackCompatibility:
    reasons = []
    current = _version(platform_version)
    minimum = manifest.get("min_platform_version")
    maximum = manifest.get("max_platform_version")
    if minimum is not None and current < _version(minimum):
        reasons.append(f"requires platform >= {minimum}")
    if maximum is not None and current > _version(maximum):
        reasons.append(f"requires platform <= {maximum}")
    supported_schemas = manifest.get("graph_schema_versions")
    if supported_schemas is not None:
        if not isinstance(supported_schemas, list) or graph_schema_version not in supported_schemas:
            reasons.append(f"graph schema v{graph_schema_version} is not supported")
    return PackCompatibility(
        compatible=not reasons,
        reasons=tuple(reasons),
        platform_version=platform_version,
        graph_schema_version=graph_schema_version,
    )
