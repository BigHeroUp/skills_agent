from __future__ import annotations

from .base import BaseAgent


class DiscoveryAgent(BaseAgent):
    name = "discovery-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Analizzo richiesta iniziale e requirement.")
        objective = (job.prompt or "").strip().split("\n")[0][:240]
        scope = {
            "primary_objective": objective or "Definire obiettivo insieme al cliente",
            "has_files": bool(job.file_paths),
            "input_types": [p.suffix.lower() for p in job.file_paths],
            "business_requirements_present": bool(job.business_requirements.strip()),
        }
        await self.emit(job_id, "complete", "info", "Discovery completata.", scope)
        return {"discovery": scope}
