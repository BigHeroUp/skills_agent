from __future__ import annotations

from .base import BaseAgent


class GovernanceAgent(BaseAgent):
    name = "governance-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Valuto compliance, rischi e completezza decisionale.")
        checks = {
            "clarification_done": bool(job.clarification_answers),
            "has_solution": "final_solution_markdown" in job.artifacts,
            "has_risk_log": "risk_log" in job.artifacts,
            "data_analyzed_if_provided": (not job.file_paths) or bool(job.artifacts.get("file_insights")) or bool(job.artifacts.get("db_insights")),
        }
        decision = "approved" if all(checks.values()) else "needs-review"
        await self.emit(job_id, "complete", "info", "Governance check completata.", {"decision": decision})
        return {"governance": {"decision": decision, "checks": checks}}
