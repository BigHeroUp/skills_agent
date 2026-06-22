from __future__ import annotations

import asyncio

from ..state import JobStore
from .analysis import AnalysisAgent
from .clarification import ClarificationAgent
from .data_intake import DataIntakeAgent
from .discovery import DiscoveryAgent
from .governance import GovernanceAgent
from .learning import LearningAgent
from .ops import OpsAgent
from .skill_registry import SKILL_REGISTRY
from .solution import SolutionAgent


class ChiefOrchestrator:
    def __init__(self, store: JobStore) -> None:
        self.store = store
        self.discovery = DiscoveryAgent(store)
        self.clarification = ClarificationAgent(store)
        self.data_intake = DataIntakeAgent(store)
        self.analysis = AnalysisAgent(store)
        self.solution = SolutionAgent(store)
        self.governance = GovernanceAgent(store)
        self.learning = LearningAgent(store)
        self.ops = OpsAgent(store)

    async def run_intake(self, job_id: str) -> None:
        await self.store.set_status(job_id, "intake")
        await self.store.append_event(job_id, "chief-orchestrator", "start", "info", "Avvio intake multi-agente.")
        await self.store.merge_artifacts(job_id, {"skill_registry": SKILL_REGISTRY})

        discovery_artifacts = await self.discovery.run(job_id)
        await self.store.merge_artifacts(job_id, discovery_artifacts)

        clarification_artifacts = await self.clarification.generate(job_id)
        await self.store.merge_artifacts(job_id, {"clarification_questions": clarification_artifacts.get("questions", [])})

        await self.store.set_status(job_id, "awaiting_clarification")
        await self.store.append_event(
            job_id,
            "chief-orchestrator",
            "pause",
            "info",
            "In attesa risposte del cliente prima di procedere.",
            {"questions": clarification_artifacts.get("questions", [])},
        )

    async def continue_after_clarification(self, job_id: str) -> None:
        await self.store.set_status(job_id, "running")
        await self.store.append_event(job_id, "chief-orchestrator", "resume", "info", "Riparto dopo chiarimenti: esecuzione pipeline.")
        job = await self.store.get_job(job_id)
        if job:
            historical_actions = await self.store.suggest_next_best_actions(
                prompt=job.prompt,
                business_requirements=job.business_requirements,
                max_items=5,
            )
            await self.store.merge_artifacts(job_id, {"learned_next_best_actions": historical_actions})
            await self.store.append_event(
                job_id,
                "learning-agent",
                "memory",
                "info",
                "Recuperate next best action dalla memoria persistente.",
                {"count": len(historical_actions)},
            )

        # Parallel block: data analysis + plan + runtime dependencies.
        data_task = asyncio.create_task(self.data_intake.run(job_id))
        analysis_task = asyncio.create_task(self.analysis.run(job_id))
        ops_task = asyncio.create_task(self.ops.run(job_id))

        data_artifacts, analysis_artifacts, ops_artifacts = await asyncio.gather(data_task, analysis_task, ops_task)
        await self.store.merge_artifacts(job_id, data_artifacts)
        await self.store.merge_artifacts(job_id, analysis_artifacts)
        await self.store.merge_artifacts(job_id, ops_artifacts)

        # Solution + governance + learning.
        solution_artifacts = await self.solution.run(job_id)
        await self.store.merge_artifacts(job_id, solution_artifacts)

        governance_artifacts = await self.governance.run(job_id)
        await self.store.merge_artifacts(job_id, governance_artifacts)

        learning_artifacts = await self.learning.run(job_id)
        await self.store.merge_artifacts(job_id, learning_artifacts)

        decision = governance_artifacts.get("governance", {}).get("decision", "needs-review")
        if decision == "approved":
            await self.store.set_status(job_id, "completed")
            await self.store.append_event(job_id, "chief-orchestrator", "complete", "success", "Pipeline completata con esito approvato.")
        else:
            await self.store.set_status(job_id, "completed-with-review")
            await self.store.append_event(job_id, "chief-orchestrator", "complete", "warning", "Pipeline completata ma richiede review.")

    async def fail_job(self, job_id: str, reason: str) -> None:
        await self.store.set_status(job_id, "failed")
        await self.store.append_event(job_id, "chief-orchestrator", "error", "error", reason)
