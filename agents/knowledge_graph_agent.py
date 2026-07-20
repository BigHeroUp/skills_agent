"""Agente finale per aggiornare il Knowledge Graph locale."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from services.knowledge_graph.analysis_mapper import map_analysis_context
from services.knowledge_graph.store import KnowledgeGraphStore
from utils.context import AgentContext


class KnowledgeGraphAgent(BaseAgent):
    """Persistenza non bloccante delle relazioni emerse dall'analisi."""

    def __init__(self, store: KnowledgeGraphStore | None = None):
        super().__init__(name="KnowledgeGraph", skill_name="knowledge_graph")
        self.store = store or KnowledgeGraphStore()

    def process(self, context: AgentContext) -> AgentContext:
        self.log("Aggiornamento knowledge graph locale...")
        try:
            with self.store.transaction():
                self.store.load()
                snapshot = map_analysis_context(context)
                for node in snapshot.nodes:
                    self.store.upsert_node(node)
                for edge in snapshot.edges:
                    self.store.upsert_edge(edge)
                saved = self.store.save()
            if not isinstance(context.metadata, dict):
                context.metadata = {}
            context.metadata["knowledge_graph"] = {
                "path": str(self.store.path),
                "node_count": len(saved.nodes),
                "edge_count": len(saved.edges),
            }
            self.log("Knowledge graph aggiornato")
        except Exception as exc:
            self.logger.warning("Knowledge graph non aggiornato: %s", exc)
        return context
