from __future__ import annotations

from ..intelligence import build_solution_markdown
from .base import BaseAgent


class SolutionAgent(BaseAgent):
    name = "solution-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Produco la migliore soluzione consolidando dati e vincoli.")
        solution_md = build_solution_markdown(
            {
                "prompt": job.prompt,
                "business_requirements": job.business_requirements,
                "clarification_answers": job.clarification_answers,
                "file_insights": job.artifacts.get("file_insights", []),
                "db_insights": job.artifacts.get("db_insights", []),
                "learned_next_best_actions": job.artifacts.get("learned_next_best_actions", []),
            }
        )
        await self.emit(job_id, "complete", "info", "Soluzione generata.")
        return {"final_solution_markdown": solution_md}
