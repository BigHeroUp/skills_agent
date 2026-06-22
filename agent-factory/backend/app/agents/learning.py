from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseAgent


class LearningAgent(BaseAgent):
    name = "learning-agent"

    async def run(self, job_id: str) -> dict:
        job = await self.store.get_job(job_id)
        if not job:
            return {}

        await self.emit(job_id, "start", "info", "Estraggo learnings e patch candidate per migliorare i prossimi run.")

        opportunities: list[str] = []
        if not job.business_requirements.strip():
            opportunities.append("Rendere obbligatorio un BR minimo per ridurre ambiguita iniziale.")
        if job.file_paths and not job.artifacts.get("file_insights"):
            opportunities.append("Rinforzare fallback di analisi dati quando pandas/openpyxl non sono disponibili.")
        if len(job.clarification_answers) < 3:
            opportunities.append("Aumentare il numero minimo di chiarimenti richiesti prima dell elaborazione finale.")
        if not opportunities:
            opportunities.append("Promuovere la configurazione corrente a baseline per task simili.")

        suggested_actions = await self.store.suggest_next_best_actions(
            prompt=job.prompt,
            business_requirements=job.business_requirements,
            max_items=5,
        )

        generated_actions = [
            "Confermare KPI e soglie di successo prima della messa in esecuzione.",
            "Inserire checkpoint di validazione dati prima della fase di soluzione.",
            "Tracciare outcome e gap per aggiornare il playbook degli agenti.",
        ]
        consolidated_actions = []
        for action in [*suggested_actions, *generated_actions]:
            if action not in consolidated_actions:
                consolidated_actions.append(action)

        governance_decision = str(job.artifacts.get("governance", {}).get("decision", "needs-review"))
        quality_score = 1.0 if governance_decision == "approved" else 0.5
        tags = [
            token
            for token in {
                *(job.prompt.lower().split()),
                *(job.business_requirements.lower().split()),
                *(path.suffix.lower() for path in job.file_paths),
                governance_decision,
            }
            if len(token) > 2
        ]
        await self.store.record_learning(
            job_id=job_id,
            tags=tags[:40],
            recommendations=consolidated_actions[:8],
            outcome=governance_decision,
            score=quality_score,
        )

        learning_report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "opportunities": opportunities,
            "next_experiments": consolidated_actions[:5],
            "historical_actions_detected": suggested_actions[:5],
            "learning_persisted": True,
        }

        await self.emit(
            job_id,
            "complete",
            "info",
            "Learning report aggiornato e salvato in memoria persistente.",
            {"opportunities": len(opportunities), "actions": len(consolidated_actions)},
        )
        return {
            "learning_report": learning_report,
            "learned_next_best_actions": consolidated_actions[:5],
        }
