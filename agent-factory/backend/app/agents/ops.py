from __future__ import annotations

from ..dependency_manager import ensure_python_packages
from .base import BaseAgent


class OpsAgent(BaseAgent):
    name = "ops-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Eseguo controlli operativi e dipendenze runtime richieste.")

        needed = []
        merged_text = f"{job.prompt} {job.business_requirements}".lower()
        if any(key in merged_text for key in ["graf", "chart", "dashboard", "plot"]):
            needed.extend(["plotly", "matplotlib"])
        if any(key in merged_text for key in ["sql", "query", "join"]):
            needed.append("duckdb")

        install_results = ensure_python_packages(needed) if needed else {}
        await self.emit(job_id, "complete", "info", "Ops check completata.", {"runtime_dependencies": install_results})
        return {"ops_runtime_dependencies": install_results}
