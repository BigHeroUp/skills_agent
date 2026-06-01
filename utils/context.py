"""
Oggetto Context condiviso tra gli agenti.
Contiene tutti i dati che passano da un agente all'altro.
"""

from dataclasses import dataclass, field
from typing import Any, List, Dict
from datetime import datetime


@dataclass
class AgentContext:
    """Context condiviso tra gli agenti"""
    
    # Input iniziale
    user_input: str = ""
    
    # Dati estratti
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Risultati validazione
    validation_results: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    
    # Dati processati
    processed_data: Dict[str, Any] = field(default_factory=dict)
    
    # Analisi e insight
    insights: Dict[str, Any] = field(default_factory=dict)
    
    # Report finale
    final_report: str = ""
    
    # Errori accumulati
    errors: List[str] = field(default_factory=list)
    
    # Metadati
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_error(self, error: str, agent: str = ""):
        """Aggiungi un errore al context"""
        msg = f"[{agent}] {error}" if agent else error
        self.errors.append(msg)
        self.is_valid = False
    
    def get_summary(self) -> str:
        """Ritorna un riepilogo del context"""
        summary = f"""═══════════════════════════════════════
📋 AGENT CONTEXT SUMMARY
═══════════════════════════════════════
User Input: {self.user_input[:50]}...
Valid: {self.is_valid}
Errors: {len(self.errors)}
Data Keys: {list(self.raw_data.keys())}
═══════════════════════════════════════"""
        return summary
    
    def __repr__(self) -> str:
        return f"AgentContext(valid={self.is_valid}, errors={len(self.errors)}, data_keys={list(self.raw_data.keys())})"
