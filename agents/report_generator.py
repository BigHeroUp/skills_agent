"""
Report Generator Agent
Crea il report finale in vari formati
"""

from agents.base_agent import BaseAgent
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.context import AgentContext


class ReportGeneratorAgent(BaseAgent):
    """Agent che genera il report finale"""
    
    def __init__(self):
        super().__init__(name="ReportGenerator", skill_name="email_writer")
        self.local_engine = SeniorDataAnalystEngine()
    
    def process(self, context: AgentContext) -> AgentContext:
        """Genera il report finale"""
        self.log("Generazione report in corso...")
        
        try:
            local_analysis = context.insights.get("local_analysis")
            if not isinstance(local_analysis, dict):
                local_analysis = self.local_engine.analyze(
                    context.processed_data,
                    user_request=context.user_input,
                )
            local_report = local_analysis.get("final_report") or self.local_engine.generate_final_report(
                local_analysis
            )

            openai_enrichment = None
            task_prompt = f"""
            Migliora esclusivamente chiarezza e stile del seguente report locale.
            Non aggiungere numeri, correlazioni, cause o conclusioni non presenti.

            {local_report[:10000]}
            """
            if self.openai_available:
                try:
                    prompt = self.build_prompt_with_skill(task_prompt)
                    openai_enrichment = self.call_openai(
                        [{"role": "user", "content": prompt}],
                        temperature=0.5,
                    )
                except Exception as exc:
                    self.logger.warning("Report OpenAI non disponibile: %s", exc)

            if openai_enrichment:
                context.final_report = (
                    f"{local_report}\n\n## Arricchimento narrativo opzionale\n{openai_enrichment}"
                )
            else:
                context.final_report = local_report
            
            self.log("✅ Report generato con successo")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
