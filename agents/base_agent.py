"""
Classe base per tutti gli agenti.
Ogni agente eredita da questa per avere accesso a OpenAI e logging.
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from dotenv import load_dotenv
from services.llm_gateway import get_llm_gateway
from utils.context import AgentContext
from utils.logging_config import get_logger


class BaseAgent(ABC):
    """Classe base per tutti gli agenti"""
    
    def __init__(self, name: str, skill_name: str = ""):
        self.name = name
        self.skill_name = skill_name or name.lower()
        self.logger = get_logger(f"agent.{self.name}")
        
        # Carica configurazione ambiente per il gateway LLM condiviso.
        load_dotenv()
        self.llm_gateway = get_llm_gateway()
        self.client = self.llm_gateway.client
        if not os.getenv("OPENAI_API_KEY"):
            self.logger.warning(
                "Configurazione OpenAI assente: l'agente usera i fallback locali disponibili"
            )
        self.model = self.llm_gateway.model

    @property
    def openai_available(self) -> bool:
        """Indica se il client OpenAI opzionale e configurato."""
        gateway = getattr(self, "llm_gateway", None)
        if gateway is not None:
            return gateway.client is not None
        return getattr(self, "client", None) is not None
    
    def load_skill_prompt(self) -> str:
        """Carica il prompt dello skill dal file SKILL.md"""
        skill_path = Path("skills") / self.skill_name / "SKILL.md"
        
        if not skill_path.exists():
            return f"Tu sei un esperto di {self.name}."
        
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()

    def build_prompt_with_skill(self, task_prompt: str) -> str:
        """Combina istruzioni della skill e prompt specifico del task."""
        skill_prompt = self.load_skill_prompt()
        return f"""ISTRUZIONI SKILL ({self.skill_name}):
{skill_prompt}

TASK CORRENTE:
{task_prompt}
"""
    
    def call_openai(
        self,
        messages: list,
        temperature: float | None = None,
        task_name: str | None = None,
        cache_key: str | None = None,
        fallback: str | dict | None = None,
    ) -> str:
        """Wrapper compatibile verso il gateway LLM centralizzato."""
        if not hasattr(self, "llm_gateway"):
            self.llm_gateway = get_llm_gateway()
            self.model = self.llm_gateway.model
        system_message = {
            "role": "system",
            "content": "Rispondi SEMPRE in italiano. Tutte le tue risposte devono essere in italiano, senza eccezioni."
        }
        result = self.llm_gateway.complete(
            [system_message] + messages,
            task_name=task_name or self.name,
            temperature=temperature,
            cache_key=cache_key,
            fallback=fallback,
        )
        usage_summary = self.llm_gateway.get_usage_summary()
        self.logger.info(
            "Richiesta OpenAI gestita. task_name=%s model=%s cached=%s status=%s calls=%s/%s",
            result.get("task_name"),
            result.get("model"),
            result.get("cached"),
            result.get("status"),
            usage_summary.get("calls_used"),
            usage_summary.get("max_calls"),
        )
        if result.get("status") == "fallback":
            self.logger.warning("OpenAI fallback usato per task=%s: %s", result.get("task_name"), result.get("error"))
        elif result.get("status") == "error":
            self.logger.warning("OpenAI non disponibile per task=%s: %s", result.get("task_name"), result.get("error"))
        return result.get("content", "")
    
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
