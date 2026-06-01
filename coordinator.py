"""
Coordinatore centrale
Orchestra il flusso di comunicazione tra gli agenti (Hub & Spoke)
"""

from agents.data_source_manager import DataSourceManagerAgent
from agents.query_suggestion_agent import QuerySuggestionAgent
from agents.data_extractor import DataExtractorAgent
from agents.data_validator import DataValidatorAgent
from agents.data_processor import DataProcessorAgent
from agents.analyst import AnalystAgent
from agents.report_generator import ReportGeneratorAgent
from utils.context import AgentContext
from utils.logging_config import get_logger
from typing import Callable, Optional
from pathlib import Path
import sys


logger = get_logger("coordinator")


def safe_print(message: str):
    """Print log messages without failing on Windows legacy consoles."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(message.encode(encoding, errors="replace").decode(encoding))


class Coordinator:
    """Coordinatore centrale che orchestra gli agenti"""
    
    def __init__(self):
        # Crea directory necessarie
        self._ensure_directories()
        
        self.agents = [
            DataSourceManagerAgent(),          # Gestore fonti dati
            QuerySuggestionAgent(),            # NEW: Suggeritore di query
            DataExtractorAgent(),
            DataValidatorAgent(),
            DataProcessorAgent(),
            AnalystAgent(),
            ReportGeneratorAgent()
        ]
        self.context: AgentContext = None
    
    def _ensure_directories(self):
        """Crea directory necessarie se non esistono"""
        directories = [
            Path("data"),
            Path("logs"),
            Path("skills/query_suggestion"),
            Path("skills/oracle_sql"),
            Path("skills/email_writer"),
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
    
    def run(
        self,
        user_input: str,
        metadata: dict = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> AgentContext:
        """
        Esegue il flusso completo di agenti.
        
        Flusso:
        0. Data Source Manager → carica dati dalla fonte
        1. Query Suggestion → suggerisce query da descrizione naturale (NUOVO)
        2. Data Extractor → estrae dati
        3. Data Validator → valida dati
        4. Data Processor → elabora dati
        5. Analyst → genera insight
        6. Report Generator → crea report
        """
        
        safe_print("\n" + "="*60)
        safe_print("INIZIO ELABORAZIONE MULTI-AGENT")
        safe_print("="*60)
        logger.info("Pipeline avviata. source_type=%s", (metadata or {}).get("source_type", "non specificata"))
        
        # Inizializza context con metadata
        self.context = AgentContext(user_input=user_input)
        if metadata:
            self.context.metadata = metadata
        
        # Esegui ogni agente in sequenza
        for index, agent in enumerate(self.agents):
            if progress_callback:
                progress_callback(agent.name, int(index / len(self.agents) * 100))
            safe_print(f"\nEsecuzione: {agent}")
            logger.info("Esecuzione agente %s (%s/%s)", agent.name, index + 1, len(self.agents))
            self.context = agent.process(self.context)
            
            # Verifica errori
            if self.context.errors:
                safe_print(f"   Errori: {len(self.context.errors)}")
                logger.warning("Pipeline con errori accumulati: %s", len(self.context.errors))
        
        safe_print("\n" + "="*60)
        safe_print("ELABORAZIONE COMPLETATA")
        safe_print("="*60)
        logger.info(
            "Pipeline completata. valida=%s errori=%s",
            self.context.is_valid,
            len(self.context.errors),
        )
        
        return self.context
    
    def get_summary(self) -> str:
        """Ritorna un riepilogo dell'elaborazione"""
        if not self.context:
            return "❌ Nessuna elaborazione eseguita"
        
        agents_list = "\n".join([f'  {i+1}. {agent.name}' for i, agent in enumerate(self.agents)])
        
        summary = f"""
╔════════════════════════════════════════╗
║     RIEPILOGO ELABORAZIONE MULTI-AGENT ║
╚════════════════════════════════════════╝

📝 Input Utente: {self.context.user_input[:50]}...

🔄 Flusso Agenti:
{agents_list}

📊 Risultati:
  - Dati Estratti: {len(self.context.raw_data)} campi
  - Validazione: {'✅ Valido' if self.context.is_valid else '❌ Non valido'}
  - Errori: {len(self.context.errors)}

{'='*40}
"""
        return summary


