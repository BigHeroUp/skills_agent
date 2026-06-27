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
            suggestion = context.raw_data.get("extraction_suggestion", {})
            source_type = context.metadata.get("source_type", suggestion.get("source", "unknown"))
            dataframe = context.raw_data.get("dataframe")
            dataframe_columns = list(getattr(dataframe, "columns", []))
            fields = dataframe_columns if dataframe_columns else suggestion.get("columns_extracted", [])
            context.raw_data["extraction_plan"] = {
                "source": source_type,
                "query": suggestion.get("query", ""),
                "fields": fields,
                "description": suggestion.get(
                    "description",
                    "Piano di estrazione locale basato sui dati gia disponibili.",
                ),
                "mode": "local",
            }
            context.raw_data["status"] = "estratti"
            
            self.log("✅ Dati estratti con successo")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
