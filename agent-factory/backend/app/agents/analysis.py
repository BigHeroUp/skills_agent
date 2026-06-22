from __future__ import annotations

from .base import BaseAgent


class AnalysisAgent(BaseAgent):
    name = "analysis-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Creo piano analitico e workstream prioritari.")
        answers = job.clarification_answers

        plan = [
            "Consolidare obiettivi e KPI in un unico contract.",
            "Validare qualita input e availability dati.",
            "Eseguire analisi esplorativa e costruire insight azionabili.",
            "Generare proposta soluzione con opzioni e tradeoff.",
            "Misurare impatto previsto e definire piano esecuzione.",
        ]

        if "graf" in (job.prompt + job.business_requirements).lower():
            plan.insert(3, "Costruire visualizzazioni comparative per i KPI chiave.")

        risk_log = [
            "Ambiguita sugli obiettivi finali.",
            "Dati incompleti o incoerenti.",
            "Vincoli non esplicitati su tempi/costi/compliance.",
        ]
        if answers:
            risk_log[0] = "Ambiguita ridotta grazie ai chiarimenti ricevuti."

        await self.emit(job_id, "complete", "info", "Piano analitico pronto.", {"steps": len(plan)})
        return {"analysis_plan": plan, "risk_log": risk_log}
