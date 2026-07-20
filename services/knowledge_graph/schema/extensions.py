"""Controlled, namespaced Knowledge Graph schema extensions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .contracts import GraphSchema, NodeTypeSpec, RelationshipSpec


PACK_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


@dataclass(frozen=True)
class DomainPackSchemaExtension:
    """Additive schema contribution owned by one Domain Pack."""

    pack_id: str
    version: str
    node_types: Mapping[str, NodeTypeSpec] = field(default_factory=dict)
    relationships: Mapping[str, RelationshipSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not PACK_ID.fullmatch(self.pack_id):
            raise ValueError("pack_id must use lower_snake_case")
        if not self.version.strip():
            raise ValueError("extension version must be non-empty")
        node_prefix = f"{self.pack_id}__"
        relationship_prefix = f"{self.pack_id.upper()}__"
        nodes = dict(sorted(self.node_types.items()))
        relationships = dict(sorted(self.relationships.items()))
        if any(name != spec.name for name, spec in nodes.items()):
            raise ValueError("node type keys must match their spec names")
        if any(not name.startswith(node_prefix) for name in nodes):
            raise ValueError(f"Domain Pack node types must start with '{node_prefix}'")
        if any(name != spec.name for name, spec in relationships.items()):
            raise ValueError("relationship keys must match their spec names")
        if any(not name.startswith(relationship_prefix) for name in relationships):
            raise ValueError(
                f"Domain Pack relationships must start with '{relationship_prefix}'"
            )
        object.__setattr__(self, "node_types", MappingProxyType(nodes))
        object.__setattr__(self, "relationships", MappingProxyType(relationships))


def extend_schema(
    schema: GraphSchema,
    extensions: tuple[DomainPackSchemaExtension, ...],
) -> GraphSchema:
    """Build a new schema; the core schema and extensions remain immutable."""

    nodes = dict(schema.node_types)
    relationships = dict(schema.relationships)
    seen_packs: set[str] = set()
    for extension in sorted(extensions, key=lambda item: item.pack_id):
        if extension.pack_id in seen_packs:
            raise ValueError(f"duplicate Domain Pack extension: {extension.pack_id}")
        seen_packs.add(extension.pack_id)
        collisions = set(nodes).intersection(extension.node_types)
        collisions.update(set(relationships).intersection(extension.relationships))
        if collisions:
            raise ValueError("schema extension collision: " + ", ".join(sorted(collisions)))
        nodes.update(extension.node_types)
        relationships.update(extension.relationships)

    known_node_types = set(nodes)
    for relationship in relationships.values():
        unknown = (set(relationship.source_types) | set(relationship.target_types)) - known_node_types
        if unknown:
            raise ValueError(
                f"relationship {relationship.name} references unknown node types: "
                + ", ".join(sorted(unknown))
            )
    suffix = "+" + ".".join(sorted(seen_packs)) if seen_packs else ""
    return GraphSchema(
        schema_id=f"{schema.schema_id}{suffix}",
        version=schema.version,
        node_types=nodes,
        relationships=relationships,
    )
