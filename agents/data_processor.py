"""
Data Processor Agent
Elabora e trasforma i dati validati
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext
from utils.data_analysis import summarize_dataframe


class DataProcessorAgent(BaseAgent):
    """Agent che elabora i dati"""
    
    def __init__(self):
        super().__init__(name="DataProcessor", skill_name="data_processing")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Elabora i dati validati"""
        self.log("Elaborazione dati in corso...")
        
        try:
            if not context.is_valid:
                context.add_error("Dati non validi, impossibile elaborare", agent=self.name)
                return context
            
            df = context.raw_data.get("dataframe")
            deterministic_summary = summarize_dataframe(df)

            # Prepara il prompt per OpenAI
            task_prompt = f"""
            Elabora questi dati validati (rispondi SEMPRE in italiano):
            Riepilogo calcolato dal dataframe reale:
            {str(deterministic_summary)[:2000]}
            
            Applica in italiano:
            1. Aggregazioni necessarie
            2. Calcoli (somme, medie, percentuali)
            3. Trasformazioni (normalizzazione, pulizia)
            4. Grouping e sorting intelligente
            
            Ritorna in italiano:
            {{
                "trasformazioni_applicate": [...],
                "statistiche_riepilogative": {{...}},
                "forma_dati": "X righe, Y colonne",
                "note_elaborazione": "..."
            }}
            """
            prompt = self.build_prompt_with_skill(task_prompt)
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
            context.processed_data = {
                "processing_report": response,
                "deterministic_summary": deterministic_summary,
                "shape": f"{deterministic_summary.get('row_count', 0)} righe, {deterministic_summary.get('column_count', 0)} colonne",
                "status": "elaborato"
            }
            
            self.log("✅ Elaborazione completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
