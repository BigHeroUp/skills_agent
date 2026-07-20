"""Versioned structural schemas for the Knowledge Graph."""

from .contracts import GraphSchema, NodeTypeSpec, PropertySpec, RelationshipSpec
from .v1 import GRAPH_SCHEMA_V1

__all__ = [
    "GRAPH_SCHEMA_V1",
    "GraphSchema",
    "NodeTypeSpec",
    "PropertySpec",
    "RelationshipSpec",
]
