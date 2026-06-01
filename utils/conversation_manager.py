"""
Conversation Manager - Gestisce storico chat e follow-up questions
Mantiene il contesto dell'analisi precedente per risposte coerenti
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from utils.logging_config import get_logger


logger = get_logger("conversation")


class ConversationMessage:
    """Rappresenta un messaggio nella conversazione"""
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        self.role = role  # "user" o "assistant"
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"Message({self.role}, {self.content[:50]}...)"


class ConversationManager:
    """Gestisce storico conversazione e follow-up questions"""
    
    def __init__(self, session_id: str = "", max_history: int = 50):
        self.session_id = session_id or str(datetime.now().timestamp())
        self.messages: List[ConversationMessage] = []
        self.max_history = max_history
        self.context: Dict[str, Any] = {}
        self.analysis_context: Dict[str, Any] = {}  # Context dell'analisi precedente
        self.logger = logger
    
    def set_analysis_context(self, context: Dict[str, Any]):
        """Salva il contesto dell'analisi per i follow-up"""
        self.analysis_context = context.copy()
        self.logger.info(f"Context analisi salvato per session {self.session_id}")
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> ConversationMessage:
        """Aggiunge un messaggio allo storico"""
        msg = ConversationMessage(role, content)
        if metadata:
            msg.metadata = metadata
        
        self.messages.append(msg)
        
        # Mantiene solo gli ultimi N messaggi
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        self.logger.info(f"Messaggio aggiunto: {role} ({len(self.content)} char)")
        return msg
    
    def add_user_message(self, content: str) -> ConversationMessage:
        """Scorciatoia per aggiungere messaggio utente"""
        return self.add_message("user", content)
    
    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None) -> ConversationMessage:
        """Scorciatoia per aggiungere messaggio assistente"""
        return self.add_message("assistant", content, metadata)
    
    def get_chat_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Ritorna lo storico chat formattato per LLM"""
        return [msg.to_dict() for msg in self.messages[-limit:]]
    
    def get_conversation_for_llm(self) -> List[Dict[str, str]]:
        """Formatta conversazione per API OpenAI"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def get_last_user_message(self) -> Optional[str]:
        """Ritorna l'ultimo messaggio utente"""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
    
    def clear_messages(self):
        """Pulisce la conversazione"""
        self.messages = []
        self.logger.info(f"Conversazione ripulita per session {self.session_id}")
    
    def get_summary(self) -> str:
        """Ritorna un riepilogo della conversazione"""
        return f"""
        Session ID: {self.session_id}
        Messaggi: {len(self.messages)}
        Inizio: {self.messages[0].timestamp.strftime('%d/%m/%Y %H:%M:%S') if self.messages else 'N/A'}
        Fine: {self.messages[-1].timestamp.strftime('%d/%m/%Y %H:%M:%S') if self.messages else 'N/A'}
        """
    
    def get_context_summary(self) -> str:
        """Ritorna un riepilogo del contesto analisi per follow-up"""
        if not self.analysis_context:
            return "Nessun contesto di analisi disponibile"
        
        return f"""
        Analisi Precedente:
        - Dati Estratti: {self.analysis_context.get('raw_data', {}).get('row_count', 'N/A')} righe
        - Colonne: {len(self.analysis_context.get('raw_data', {}).get('columns', []))}
        - Valido: {'✅' if self.analysis_context.get('is_valid') else '❌'}
        - Insights: {len(self.analysis_context.get('insights', {}))} generati
        """
    
    def save_to_file(self, path: str = None):
        """Salva la conversazione su file JSON"""
        if path is None:
            path = f"data/conversations/{self.session_id}.json"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [msg.to_dict() for msg in self.messages],
            "context": self.analysis_context
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Conversazione salvata: {path}")
    
    @staticmethod
    def load_from_file(path: str) -> "ConversationManager":
        """Carica una conversazione da file JSON"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        manager = ConversationManager(session_id=data['session_id'])
        
        # Ricrea messaggi
        for msg_data in data.get('messages', []):
            msg = ConversationMessage(
                role=msg_data['role'],
                content=msg_data['content'],
                timestamp=datetime.fromisoformat(msg_data['timestamp'])
            )
            msg.metadata = msg_data.get('metadata', {})
            manager.messages.append(msg)
        
        manager.analysis_context = data.get('context', {})
        
        logger.info(f"Conversazione caricata: {path}")
        return manager
    
    def export_as_markdown(self) -> str:
        """Esporta conversazione come markdown"""
        md = f"# Conversazione {self.session_id}\n\n"
        md += f"**Inizio:** {self.messages[0].timestamp.strftime('%d/%m/%Y %H:%M:%S') if self.messages else 'N/A'}\n\n"
        
        for msg in self.messages:
            role = "👤 Utente" if msg.role == "user" else "🤖 Assistente"
            md += f"## {role}\n{msg.content}\n\n"
        
        return md
