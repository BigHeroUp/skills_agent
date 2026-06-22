from __future__ import annotations

from ..intelligence import generate_clarification_questions
from .base import BaseAgent


class ClarificationAgent(BaseAgent):
    name = "clarification-agent"

    async def generate(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {"questions": []}

        await self.emit(job_id, "start", "info", "Genero domande di chiarimento per eliminare ambiguita.")
        questions = generate_clarification_questions(job.prompt, job.business_requirements, job.uploaded_files)
        await self.store.set_questions(job_id, questions)
        await self.emit(job_id, "complete", "info", "Domande di chiarimento pronte.", {"count": len(questions)})
        return {"questions": questions}
