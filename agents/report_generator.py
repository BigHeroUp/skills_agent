"""
Report Generator Agent
Crea il report finale in vari formati
"""

from agents.base_agent import BaseAgent
from utils.context import AgentContext


class ReportGeneratorAgent(BaseAgent):
    """Agent che genera il report finale"""
    
    def __init__(self):
        super().__init__(name="ReportGenerator", skill_name="email_writer")
    
    def process(self, context: AgentContext) -> AgentContext:
        """Genera il report finale"""
        self.log("Generazione report in corso...")
        
        try:
            # Prepara il prompt per OpenAI
            prompt = f"""
            Crea un report professionale COMPLETAMENTE IN ITALIANO con:
            
            Insight: {str(context.insights)[:200]}
            Dati Processati: {str(context.processed_data)[:200]}
            
            Formato del report (tutto in ITALIANO):
            1. Riepilogo Esecutivo
            2. Scoperte Principali
            3. Analisi Dettagliata
            4. Raccomandazioni
            5. Prossimi Passi
            
            Tono: Professionale, chiaro, conciso - SEMPRE IN ITALIANO
            """
            
            messages = [{"role": "user", "content": prompt}]
            response = self.call_openai(messages, temperature=0.5)
            
            # Compila il report finale
            final_report = f"""
╔════════════════════════════════════════╗
║       ANALISI DATI - REPORT FINALE     ║
╚════════════════════════════════════════╝

📊 REPORT GENERATO
{'='*40}

{response}

{'='*40}
📌 Metadati
- Errori incontrati: {len(context.errors)}
- Status finale: {'✅ SUCCESSO' if not context.errors else '⚠️ COMPLETATO CON AVVISI'}
"""
            
            context.final_report = final_report
            
            self.log("✅ Report generato con successo")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
