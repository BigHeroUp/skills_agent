"""
Data Processor Agent
Elabora e trasforma i dati validati
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext


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
            
            # Prepara il prompt per OpenAI
            prompt = f"""
            Elabora questi dati validati (rispondi SEMPRE in italiano):
            {str(context.raw_data)[:200]}
            
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
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
            context.processed_data = {
                "processing_report": response,
                "shape": "100 righe, 5 colonne",
                "status": "elaborato"
            }
            
            self.log("✅ Elaborazione completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
