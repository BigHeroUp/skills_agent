"""Explicit Knowledge Graph lifecycle foundation."""

from .migration import GraphMigration, GraphMigrationService, MigrationPlan, MigrationRegistry
from .persistence import (
    ConcurrentGraphChange,
    FilesystemGraphPersistence,
    GraphPersistencePort,
    GraphWriteReceipt,
)
from .repair import GraphRepair, GraphRepairService, RepairPlan

__all__ = [
    "ConcurrentGraphChange",
    "FilesystemGraphPersistence",
    "GraphMigration",
    "GraphMigrationService",
    "GraphPersistencePort",
    "GraphRepair",
    "GraphRepairService",
    "GraphWriteReceipt",
    "MigrationPlan",
    "MigrationRegistry",
    "RepairPlan",
]
