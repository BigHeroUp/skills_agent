"""
Classe base per tutti gli agenti.
Ogni agente eredita da questa per avere accesso a OpenAI e logging.
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from utils.context import AgentContext
from utils.logging_config import get_logger


class BaseAgent(ABC):
    """Classe base per tutti gli agenti"""
    
    def __init__(self, name: str, skill_name: str = ""):
        self.name = name
        self.skill_name = skill_name or name.lower()
        self.logger = get_logger(f"agent.{self.name}")
        
        # Carica API key
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("Configurazione OpenAI assente")
            raise ValueError("❌ OPENAI_API_KEY non trovata in .env")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
    
    def load_skill_prompt(self) -> str:
        """Carica il prompt dello skill dal file SKILL.md"""
        skill_path = Path("skills") / self.skill_name / "SKILL.md"
        
        if not skill_path.exists():
            return f"Tu sei un esperto di {self.name}."
        
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def call_openai(self, messages: list, temperature: float = 0.7) -> str:
        """Chiama l'API OpenAI e ritorna la risposta"""
        try:
            self.logger.info("Richiesta OpenAI avviata. model=%s", self.model)
            # Aggiungi sistema message per forzare italiano
            system_message = {
                "role": "system",
                "content": "Rispondi SEMPRE in italiano. Tutte le tue risposte devono essere in italiano, senza eccezioni."
            }
            
            # Inserisci system message all'inizio
            messages_with_system = [system_message] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_system,
                temperature=temperature
            )
            self.logger.info("Richiesta OpenAI completata")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error("Richiesta OpenAI fallita: %s", type(e).__name__)
            raise Exception(f"❌ Errore OpenAI in {self.name}: {str(e)}")
    
    def log(self, message: str):
        """Log di debug"""
        safe_message = (
            message.replace("✅", "OK")
            .replace("❌", "ERRORE")
            .replace("⚠️", "AVVISO")
            .replace("⚠", "AVVISO")
        )
        output = f"[{self.name}] {safe_message}"
        self.logger.info(safe_message)
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(output.encode(encoding, errors="replace").decode(encoding))
    
    @abstractmethod
    def process(self, context: AgentContext) -> AgentContext:
        """
        Metodo astratto che ogni agente deve implementare.
        Riceve un context e ritorna il context arricchito.
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.name}Agent"
