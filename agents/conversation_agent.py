"""
Conversation Agent - Risponde a follow-up questions sull'analisi
Mantiene coerenza con il contesto dell'analisi precedente
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext
from utils.conversation_manager import ConversationManager
from pathlib import Path
from typing import Dict, Any, Optional


class ConversationAgent(BaseAgent):
    """Agent specializzato nel rispondere a domande di follow-up"""
    
    def __init__(self):
        super().__init__(name="Conversation", skill_name="conversation")
        self._ensure_skill_file()
    
    def _ensure_skill_file(self):
        """Crea il file SKILL.md se non esiste"""
        skill_path = Path("skills") / self.skill_name / "SKILL.md"
        if not skill_path.exists():
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(self._get_skill_content())
            self.logger.info(f"Skill file creato: {skill_path}")
    
    def _get_skill_content(self) -> str:
        """Ritorna il contenuto del SKILL.md"""
        return """# Conversation Skill

## Descrizione
Agent specializzato nel mantenere conversazioni coerenti con l'utente su un'analisi di dati precedente. Risponde a domande di follow-up, fornisce spiegazioni approfondite e suggerisce azioni based sui dati.

## Capabilities
- Rispondere a domande specifiche sui grafici
- Fornire spiegazioni dettagliate dei risultati
- Identificare anomalie e trend nei dati
- Suggerire approfondimenti sui dati
- Mantenere coerenza con l'analisi precedente
- Generare nuove ipotesi e raccomandazioni

## System Prompt
Tu sei un assistente esperto di data analysis che sta conversando con un utente su un'analisi di dati che abbiamo già completato insieme. 

La tua specialità è:
1. **Comprendi le domande**: L'utente potrebbe chiedere dettagli su grafici, anomalie, trend
2. **Usa il contesto**: Hai accesso ai dati, insights e risultati dell'analisi precedente
3. **Spiega chiaramente**: Fornisci spiegazioni tecniche ma comprensibili
4. **Suggerisci azioni**: Quando appropriato, suggerisci ulteriori analisi o approfondimenti
5. **Mantieni professionalità**: Rispondi sempre in italiano con tono professionale

## Constraints
- Usa SOLO i dati dall'analisi precedente
- Non inventare dati o risultati che non esistono
- Se la domanda richiede nuovi dati, suggerisci di effettuare una nuova analisi
- Cita sempre i grafici/metriche quando rilevante

## Examples

### Esempio 1: Domanda su un Grafico
**Input**: "Perché il grafico di vendite mostra un picco a luglio?"
**Output**: "Nel grafico delle vendite mensili, si osserva un picco a luglio con un aumento del 25% rispetto a giugno. Questo potrebbe essere dovuto a [possibili cause da dati]... Nei dati vedo che..."

### Esempio 2: Richiesta di Approfondimento
**Input**: "Quali sono le regioni con le vendite più basse?"
**Output**: "Analizzando i dati per regione, le regioni con performance minore sono... Suggerisco di investigare ulteriormente..."

### Esempio 3: Anomalia
**Input**: "Vedo un calo improvviso, è un problema?"
**Output**: "Sì, noto anch'io un calo improvviso del X%. Osservando i dati, potrebbe essere causato da..."
"""
    
    def process(self, context: AgentContext) -> AgentContext:
        """
        Non utilizzato direttamente - questo agente è controllato dalla dashboard
        Le risposte vengono generate tramite answer_followup_question
        """
        return context
    
    def answer_followup_question(
        self,
        question: str,
        previous_context: Dict[str, Any],
        conversation_history: list = None
    ) -> str:
        """
        Risponde a una domanda di follow-up
        
        Args:
            question: La domanda dell'utente
            previous_context: Il context dell'analisi precedente
            conversation_history: Storico conversazione per coerenza
        
        Returns:
            La risposta dell'agente
        """
        try:
            self.log(f"Risposta a domanda follow-up: {question[:50]}...")
            
            # Costruisce il prompt con il contesto
            prompt = self._build_prompt(question, previous_context, conversation_history)
            
            messages = [{"role": "user", "content": self.build_prompt_with_skill(prompt)}]
            response = self.call_openai(messages, temperature=0.5)
            
            self.log("✅ Risposta generata")
            return response
            
        except Exception as e:
            self.log(f"❌ Errore: {e}")
            raise Exception(f"Errore nella generazione della risposta: {str(e)}")
    
    def _build_prompt(
        self,
        question: str,
        previous_context: Dict[str, Any],
        conversation_history: list = None
    ) -> str:
        """Costruisce il prompt per OpenAI con il contesto"""
        
        # Estrae informazioni utili dal contesto
        raw_data = previous_context.get('raw_data', {})
        insights = previous_context.get('insights', {})
        processed_data = previous_context.get('processed_data', {})
        
        # Formatta il contesto
        context_summary = f"""
CONTESTO ANALISI PRECEDENTE:
- Dati: {raw_data.get('row_count', 'N/A')} righe, {len(raw_data.get('columns', []))} colonne
- Colonne disponibili: {', '.join(raw_data.get('columns', [])[:5])}...
- Insights generati: {len(insights)} principali
- Validazione dati: {'✅ Validi' if previous_context.get('is_valid') else '❌ Non validi'}

INSIGHTS PRECEDENTI:
{self._format_insights(insights)}

DATI PROCESSATI:
{self._format_processed_data(processed_data)}
"""
        
        # Aggiunge storico conversazione se disponibile
        history_text = ""
        if conversation_history:
            history_text = "\nSTORICO CONVERSAZIONE:\n"
            for msg in conversation_history[-5:]:  # Ultimi 5 messaggi
                history_text += f"- {msg['role']}: {msg['content'][:100]}...\n"
        
        prompt = f"""Tu sei un assistente esperto di data analysis.

{context_summary}
{history_text}

DOMANDA DELL'UTENTE:
{question}

Rispondi in italiano, usa il contesto dell'analisi precedente e cita i dati specifici quando possibile.
Se la domanda richiede nuovi dati non disponibili, suggerisci di effettuare una nuova analisi.
"""
        
        return prompt
    
    def _format_insights(self, insights: Dict[str, Any]) -> str:
        """Formatta gli insights per il prompt"""
        if not insights:
            return "Nessun insight disponibile"
        
        lines = []
        for key, value in list(insights.items())[:5]:  # Prime 5
            if isinstance(value, str):
                lines.append(f"- {key}: {value[:100]}")
            else:
                lines.append(f"- {key}: {str(value)[:100]}")
        
        return "\n".join(lines)
    
    def _format_processed_data(self, processed_data: Dict[str, Any]) -> str:
        """Formatta i dati processati per il prompt"""
        if not processed_data:
            return "Nessun dato processato disponibile"
        
        lines = []
        for key, value in list(processed_data.items())[:5]:  # Prime 5
            if isinstance(value, (int, float)):
                lines.append(f"- {key}: {value}")
            elif isinstance(value, str):
                lines.append(f"- {key}: {value[:80]}")
            elif isinstance(value, list):
                lines.append(f"- {key}: {len(value)} elementi")
            else:
                lines.append(f"- {key}: {str(value)[:80]}")
        
        return "\n".join(lines) if lines else "Dati processati disponibili"
