"""Agente deterministico per arricchire il context con reasoning dal Knowledge Graph."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from services.knowledge_graph.reasoning_engine import (
    KnowledgeReasoningEngine,
    build_dataset_profile_from_context,
)
from utils.context import AgentContext


class KnowledgeReasoningAgent(BaseAgent):
    """Arricchisce il context con memoria analitica senza usare OpenAI."""

    def __init__(self, reasoning_engine: KnowledgeReasoningEngine | None = None):
        super().__init__(name="KnowledgeReasoning", skill_name="knowledge_graph")
        self.reasoning_engine = reasoning_engine or KnowledgeReasoningEngine()

    def process(self, context: AgentContext) -> AgentContext:
        self.log("Reasoning su knowledge graph in corso...")
        initial_validity = context.is_valid
        try:
            graph_path = (context.metadata or {}).get("knowledge_graph_path")
            reasoning_engine = (
                KnowledgeReasoningEngine(path=str(graph_path))
                if graph_path
                else self.reasoning_engine
            )
            current_profile = build_dataset_profile_from_context(context)
            reasoning_context = reasoning_engine.build_reasoning_context_for_analysis(
                current_profile
            )
            context.knowledge_reasoning_context = reasoning_context
            context.recommended_analytical_steps = (
                reasoning_context.get("recommendations", {}).get("recommended_steps", []) or []
            )

            if not isinstance(context.processed_data, dict):
                context.processed_data = {}
            context.processed_data["knowledge_reasoning_context"] = context.knowledge_reasoning_context
            context.processed_data["recommended_analytical_steps"] = context.recommended_analytical_steps

            similar_runs = reasoning_context.get("similarity", {}).get("similar_runs", [])
            self.log(
                "Knowledge reasoning completato: "
                f"similar_runs={len(similar_runs)} "
                f"recommended_steps={len(context.recommended_analytical_steps)}"
            )
        except Exception as exc:
            self.logger.warning("Knowledge reasoning non disponibile: %s", exc)
            if not isinstance(context.knowledge_reasoning_context, dict):
                context.knowledge_reasoning_context = {}
            context.knowledge_reasoning_context.setdefault("status", "skipped")
            context.knowledge_reasoning_context.setdefault("error", str(exc))
            if not isinstance(context.recommended_analytical_steps, list):
                context.recommended_analytical_steps = []
            context.is_valid = initial_validity
        return context
