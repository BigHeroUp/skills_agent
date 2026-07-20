"""Minimal governance policy for lossless structural validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from services.knowledge_graph.domain.issues import IssueSeverity
from services.knowledge_graph.schema import (
    GRAPH_SCHEMA_V1,
    DomainPackSchemaExtension,
    GraphSchema,
    extend_schema,
)


class ValidationMode(str, Enum):
    PERMISSIVE = "permissive"
    STRICT = "strict"


@dataclass(frozen=True)
class GovernancePolicy:
    policy_id: str
    version: str
    schema: GraphSchema
    allow_missing_schema_version_as_v1: bool = True
    unknown_node_type_severity: IssueSeverity = IssueSeverity.WARNING
    unknown_relationship_severity: IssueSeverity = IssueSeverity.WARNING
    missing_label_severity: IssueSeverity = IssueSeverity.WARNING
    missing_properties_severity: IssueSeverity = IssueSeverity.WARNING
    issue_severity_overrides: Mapping[str, IssueSeverity] = field(default_factory=dict)
    extensions: tuple[DomainPackSchemaExtension, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "issue_severity_overrides",
            MappingProxyType(dict(sorted(self.issue_severity_overrides.items()))),
        )
        ordered_extensions = tuple(sorted(self.extensions, key=lambda item: item.pack_id))
        object.__setattr__(self, "extensions", ordered_extensions)
        if ordered_extensions:
            object.__setattr__(self, "schema", extend_schema(self.schema, ordered_extensions))

    def severity_for(self, code: str, default: IssueSeverity) -> IssueSeverity:
        return self.issue_severity_overrides.get(code, default)


GOVERNANCE_POLICY_V1 = GovernancePolicy(
    policy_id="veraxis.knowledge_graph.structural.v1",
    version="1.0.0",
    schema=GRAPH_SCHEMA_V1,
)
