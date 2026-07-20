"""Final non-blocking agent for the integrated product intelligence flow."""

from __future__ import annotations

from pathlib import Path

from agents.base_agent import BaseAgent
from services.integrated_product_flow import IntegratedProductFlow
from services.knowledge_graph.store import KnowledgeGraphStore
from utils.context import AgentContext


class ProductIntelligenceAgent(BaseAgent):
    def __init__(self, flow: IntegratedProductFlow | None = None):
        super().__init__(name="ProductIntelligence", skill_name="knowledge_graph")
        self.flow = flow

    def process(self, context: AgentContext) -> AgentContext:
        if (context.metadata or {}).get("integrated_product_flow", True) is False:
            context.product_intelligence = {
                "status": "disabled",
                "execution_type": "integrated_product_intelligence",
            }
            return context
        try:
            graph_metadata = (context.metadata or {}).get("knowledge_graph") or {}
            graph_path = Path(graph_metadata.get("path") or KnowledgeGraphStore.DEFAULT_PATH)
            experience_path = (context.metadata or {}).get("experience_path")
            flow = self.flow or IntegratedProductFlow(
                kg_path=graph_path,
                experience_path=experience_path,
            )
            context.product_intelligence = flow.run(context)
            if not isinstance(context.processed_data, dict):
                context.processed_data = {}
            context.processed_data["product_intelligence"] = context.product_intelligence
        except Exception as exc:
            self.logger.warning("Integrated product intelligence unavailable: %s", exc)
            context.product_intelligence = {
                "status": "error",
                "message": str(exc),
                "execution_type": "integrated_product_intelligence",
            }
        return context
