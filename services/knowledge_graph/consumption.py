"""Read-only governance facade for Knowledge Graph consumers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.knowledge_graph.governance import (
    GOVERNANCE_POLICY_V1,
    GovernancePolicy,
    ValidationMode,
)
from services.knowledge_graph.models import (
    KnowledgeEdge,
    KnowledgeGraphSnapshot,
    KnowledgeNode,
)
from services.knowledge_graph.store import KnowledgeGraphStore
from services.knowledge_graph.validation import GraphValidationResult, validate_graph


class ConsumerGovernanceMode(str, Enum):
    LEGACY = "legacy"
    OBSERVE = "observe"
    ENFORCE = "enforce"


class GraphConsumptionBlocked(RuntimeError):
    def __init__(self, result: GraphValidationResult):
        self.result = result
        super().__init__(
            "Knowledge Graph consumption blocked: "
            f"status={result.report.status.value}, "
            f"errors={result.report.severity_counts.get('error', 0)}"
        )


@dataclass(frozen=True)
class GovernedGraphLoad:
    snapshot: KnowledgeGraphSnapshot
    mode: ConsumerGovernanceMode
    validation: GraphValidationResult | None = None

    @property
    def is_governed(self) -> bool:
        return self.validation is not None


class GovernedGraphReader:
    """Adopt governance without adding writes or changing the legacy default."""

    def __init__(
        self,
        store: KnowledgeGraphStore,
        *,
        policy: GovernancePolicy = GOVERNANCE_POLICY_V1,
    ) -> None:
        self.store = store
        self.policy = policy

    def load(
        self,
        mode: ConsumerGovernanceMode | str = ConsumerGovernanceMode.LEGACY,
    ) -> GovernedGraphLoad:
        resolved_mode = (
            mode if isinstance(mode, ConsumerGovernanceMode) else ConsumerGovernanceMode(mode)
        )
        if resolved_mode == ConsumerGovernanceMode.LEGACY:
            return GovernedGraphLoad(self.store.load(), resolved_mode)

        validation_mode = (
            ValidationMode.STRICT
            if resolved_mode == ConsumerGovernanceMode.ENFORCE
            else ValidationMode.PERMISSIVE
        )
        result = validate_graph(
            self.store.path,
            mode=validation_mode,
            policy=self.policy,
        )
        if resolved_mode == ConsumerGovernanceMode.OBSERVE:
            return GovernedGraphLoad(self.store.load(), resolved_mode, result)
        if not result.can_consume:
            raise GraphConsumptionBlocked(result)
        return GovernedGraphLoad(self._accepted_snapshot(result), resolved_mode, result)

    @staticmethod
    def _accepted_snapshot(result: GraphValidationResult) -> KnowledgeGraphSnapshot:
        return KnowledgeGraphSnapshot(
            schema_version=result.report.graph_schema_version or 1,
            nodes=[KnowledgeNode.from_dict(dict(item)) for item in result.accepted_nodes],
            edges=[KnowledgeEdge.from_dict(dict(item)) for item in result.accepted_edges],
        )
