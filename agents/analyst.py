"""
Analyst Agent
Analizza i dati e genera insight
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext
from utils.data_analysis import build_deterministic_insights


class AnalystAgent(BaseAgent):
    """Agent che analizza i dati"""
    
    def __init__(self):
        super().__init__(name="Analyst", skill_name="analysis")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Analizza i dati processati"""
        self.log("Analisi dati in corso...")
        
        try:
            if not context.processed_data:
                context.add_error("Nessun dato processato da analizzare", agent=self.name)
                return context
            
            deterministic_summary = context.processed_data.get("deterministic_summary", {})
            deterministic_insights = build_deterministic_insights(deterministic_summary)

            # Prepara il prompt per OpenAI
            prompt = f"""
            Analizza questi dati processati (rispondi SEMPRE in italiano):
            Risultati calcolati dal dataframe reale:
            {str(deterministic_insights)[:2000]}
            
            Genera insight in italiano su:
            1. Trend principali
            2. Anomalie significative
            3. Correlazioni interessanti
            4. Raccomandazioni d'azione
            5. KPI importanti
            
            Ritorna in italiano:
            {{
                "scoperte_chiave": [...],
                "trend": [...],
                "anomalie": [...],
                "raccomandazioni": [...],
                "livello_confidenza": 0-100
            }}
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
            context.insights = {
                "analysis_report": response,
                "deterministic_insights": deterministic_insights,
                "key_metrics": deterministic_insights.get("key_metrics", {}),
                "status": "analizzato"
            }
            
            self.log("✅ Analisi completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
