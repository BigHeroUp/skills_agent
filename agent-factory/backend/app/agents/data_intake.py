from __future__ import annotations

from ..intelligence import analyze_tabular_files
from .base import BaseAgent


class DataIntakeAgent(BaseAgent):
    name = "data-intake-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Analizzo file allegati e preparo insight tabellari.")
        if not job.file_paths:
            await self.emit(job_id, "complete", "info", "Nessun file allegato da analizzare.", {"files": 0})
            return {"file_insights": []}

        artifacts, install_results = analyze_tabular_files(
            job.file_paths,
            natural_language_request=f"{job.prompt}\n{job.business_requirements}",
        )
        await self.emit(
            job_id,
            "complete",
            "info",
            "Analisi dati completata.",
            {"files": len(job.file_paths), "dependency_install": install_results},
        )
        artifacts["dependency_install"] = install_results
        return artifacts
