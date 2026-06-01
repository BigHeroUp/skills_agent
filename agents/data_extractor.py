"""
Data Extractor Agent
Estrae dati da varie fonti (database, CSV, API, ecc.)
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext


class DataExtractorAgent(BaseAgent):
    """Agent che estrae dati"""
    
    def __init__(self):
        super().__init__(name="DataExtractor", skill_name="oracle_sql")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Estrae dati in base al user input"""
        self.log(f"Estrazione dati da: {context.user_input[:40]}...")
        
        try:
            # Prepara il prompt per OpenAI
            prompt = f"""
            L'utente ha richiesto: {context.user_input}
            
            Genera un piano di estrazione dati in ITALIANO:
            1. Quale fonte dati usare (Oracle, CSV, API)?
            2. Quale query/filtro applicare?
            3. Quali campi estrarre?
            
            Ritorna un JSON con (tutto in italiano):
            {{
                "source": "...",
                "query": "...",
                "fields": [...],
                "description": "..."
            }}
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages)
            
            # Conserva i dati caricati dal source manager e aggiunge il piano AI.
            context.raw_data["extraction_plan"] = response
            context.raw_data["status"] = "estratti"
            
            self.log("✅ Dati estratti con successo")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
