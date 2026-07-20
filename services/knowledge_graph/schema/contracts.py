"""Immutable descriptive contracts for Knowledge Graph schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class DeprecationSpec:
    since: str
    replacement: str | None = None
    removal_version: int | None = None


@dataclass(frozen=True)
class CardinalitySpec:
    max_per_source: int | None = None
    max_per_target: int | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("max_per_source", self.max_per_source),
            ("max_per_target", self.max_per_target),
        ):
            if value is not None and (isinstance(value, bool) or value < 1):
                raise ValueError(f"{name} must be a positive integer or None")


@dataclass(frozen=True)
class PropertySpec:
    name: str
    required: bool = False
    recommended: bool = False
    deprecation: DeprecationSpec | None = None


@dataclass(frozen=True)
class NodeTypeSpec:
    name: str
    properties: tuple[PropertySpec, ...] = field(default_factory=tuple)
    isolated_severity: str = "warning"
    deprecation: DeprecationSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", tuple(self.properties))

    @property
    def required_properties(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.properties if item.required)

    @property
    def recommended_properties(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.properties if item.recommended)


@dataclass(frozen=True)
class RelationshipSpec:
    name: str
    source_types: frozenset[str]
    target_types: frozenset[str]
    allows_self_loop: bool = False
    canonical_name: str | None = None
    cardinality: CardinalitySpec = field(default_factory=CardinalitySpec)
    deprecation: DeprecationSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_types", frozenset(self.source_types))
        object.__setattr__(self, "target_types", frozenset(self.target_types))

    @property
    def is_legacy_alias(self) -> bool:
        return bool(self.canonical_name and self.canonical_name != self.name)

    @property
    def is_deprecated(self) -> bool:
        return self.deprecation is not None or self.is_legacy_alias


@dataclass(frozen=True)
class GraphSchema:
    schema_id: str
    version: int
    node_types: Mapping[str, NodeTypeSpec]
    relationships: Mapping[str, RelationshipSpec]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "node_types",
            MappingProxyType(dict(sorted(self.node_types.items()))),
        )
        object.__setattr__(
            self,
            "relationships",
            MappingProxyType(dict(sorted(self.relationships.items()))),
        )

    def node_spec(self, node_type: str) -> NodeTypeSpec | None:
        return self.node_types.get(node_type)

    def relationship_spec(self, relationship: str) -> RelationshipSpec | None:
        return self.relationships.get(relationship)
