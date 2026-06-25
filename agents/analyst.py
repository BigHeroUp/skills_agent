"""
Analyst Agent
Analizza i dati e genera insight
"""

from agents.base_agent import BaseAgent
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.context import AgentContext
from utils.data_analysis import build_deterministic_insights


class AnalystAgent(BaseAgent):
    """Agent che analizza i dati"""
    
    def __init__(self):
        super().__init__(name="Analyst", skill_name="analysis")
        self.local_engine = SeniorDataAnalystEngine()
    
    def process(self, context: AgentContext) -> AgentContext:
        """Analizza i dati processati"""
        self.log("Analisi dati in corso...")
        
        try:
            if not context.processed_data:
                context.add_error("Nessun dato processato da analizzare", agent=self.name)
                return context
            
            deterministic_summary = context.processed_data.get("deterministic_summary", {})
            deterministic_insights = build_deterministic_insights(deterministic_summary)
            local_analysis = self.local_engine.analyze(
                context.processed_data,
                user_request=context.user_input,
            )

            openai_enrichment = None
            task_prompt = f"""
            Arricchisci stilisticamente questa analisi locale senza modificare,
            stimare o inventare alcun valore (rispondi SEMPRE in italiano):
            {str(local_analysis)[:6000]}
            
            Produci solo una nota narrativa opzionale. I risultati numerici e le
            conclusioni fattuali devono restare quelli del motore locale.
            """
            if self.openai_available:
                try:
                    prompt = self.build_prompt_with_skill(task_prompt)
                    openai_enrichment = self.call_openai([{"role": "user", "content": prompt}])
                except Exception as exc:
                    self.logger.warning("Arricchimento OpenAI non disponibile: %s", exc)
            
            context.insights = {
                "local_analysis": local_analysis,
                "executive_summary": local_analysis["executive_summary"],
                "key_findings": local_analysis["key_findings"],
                "kpi_summary": local_analysis["kpi_summary"],
                "trend_analysis": local_analysis["trend_analysis"],
                "anomaly_analysis": local_analysis["anomaly_analysis"],
                "segmentation_analysis": local_analysis["segmentation_analysis"],
                "data_quality_notes": local_analysis["data_quality_notes"],
                "operational_recommendations": local_analysis["operational_recommendations"],
                "local_final_report": local_analysis["final_report"],
                "analysis_report": openai_enrichment or local_analysis["final_report"],
                "openai_enrichment": openai_enrichment,
                "deterministic_insights": deterministic_insights,
                "key_metrics": deterministic_insights.get("key_metrics", {}),
                "status": "analizzato",
                "analysis_mode": "local_with_openai_enrichment" if openai_enrichment else "local_only",
            }
            
            self.log("✅ Analisi completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
