"""Versioned structural schemas for the Knowledge Graph."""

from .contracts import (
    CardinalitySpec,
    DeprecationSpec,
    GraphSchema,
    NodeTypeSpec,
    PropertySpec,
    RelationshipSpec,
)
from .extensions import DomainPackSchemaExtension, extend_schema
from .v1 import GRAPH_SCHEMA_V1

__all__ = [
    "CardinalitySpec",
    "DeprecationSpec",
    "DomainPackSchemaExtension",
    "GRAPH_SCHEMA_V1",
    "GraphSchema",
    "NodeTypeSpec",
    "PropertySpec",
    "RelationshipSpec",
    "extend_schema",
]
