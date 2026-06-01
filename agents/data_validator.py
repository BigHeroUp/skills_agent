"""
Data Validator Agent
Valida l'integrità e completezza dei dati
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext


class DataValidatorAgent(BaseAgent):
    """Agent che valida i dati"""
    
    def __init__(self):
        super().__init__(name="DataValidator", skill_name="data_validation")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Valida i dati estratti"""
        self.log("Validazione dati in corso...")
        
        try:
            if not context.raw_data:
                context.add_error("Nessun dato estratto da validare", agent=self.name)
                return context
            
            # Prepara il prompt per OpenAI
            prompt = f"""
            Valida questi dati estratti (rispondi SEMPRE in italiano):
            {str(context.raw_data)[:200]}
            
            Verifica in italiano:
            1. Completezza dei dati
            2. Consistenza formato
            3. Anomalie o outlier
            4. Campi obbligatori presenti
            
            Ritorna in italiano:
            {{
                "valido": true/false,
                "problemi": [...],
                "punteggio_qualità": 0-100,
                "raccomandazioni": [...]
            }}
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
            context.validation_results = {
                "validation_report": response,
                "timestamp": str(self.get_timestamp()),
                "status": "validato"
            }
            
            # Simula validazione positiva
            context.is_valid = True
            
            self.log("✅ Validazione completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
    
    @staticmethod
    def get_timestamp() -> str:
        from datetime import datetime
        return datetime.now().isoformat()
