"""
Data Validator Agent
Valida l'integrità e completezza dei dati
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext
import pandas as pd


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

            dataframe = context.raw_data.get("dataframe")
            problems = []
            quality_score = 100
            if isinstance(dataframe, pd.DataFrame):
                if dataframe.empty:
                    problems.append("Dataframe vuoto")
                    quality_score = 0
                missing_cells = int(dataframe.isna().sum().sum())
                if missing_cells:
                    problems.append(f"{missing_cells} celle mancanti")
                    quality_score = max(0, quality_score - 10)
                duplicate_rows = int(dataframe.duplicated().sum())
                if duplicate_rows:
                    problems.append(f"{duplicate_rows} righe duplicate")
                    quality_score = max(0, quality_score - 5)
            else:
                problems.append("Dataframe non disponibile nel contesto")
                quality_score = 50
            response = {
                "valido": quality_score > 0,
                "problemi": problems,
                "punteggio_qualita": quality_score,
                "raccomandazioni": [
                    "Verificare celle mancanti e duplicati prima di usare KPI operativi."
                ] if problems else [],
                "mode": "local",
            }
            
            context.validation_results = {
                "validation_report": response,
                "timestamp": str(self.get_timestamp()),
                "status": "validato"
            }
            
            context.is_valid = bool(response["valido"])
            
            self.log("✅ Validazione completata")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
    
    @staticmethod
    def get_timestamp() -> str:
        from datetime import datetime
        return datetime.now().isoformat()
