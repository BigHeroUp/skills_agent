"""
Query Suggestion Agent
Interpreta descrizioni naturali e suggerisce query ottimali.
Apprende dalle query passate tramite QueryHistoryManager.
"""

import json
from pathlib import Path
from agents.base_agent import BaseAgent
from utils.context import AgentContext
from utils.query_history_manager import QueryHistoryManager


class QuerySuggestionAgent(BaseAgent):
    """Agent che suggerisce query basato su descrizioni naturali e learning"""
    
    def __init__(self):
        super().__init__(name="QuerySuggestion", skill_name="query_suggestion")
        self.history_manager = QueryHistoryManager()
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
        return """# Query Suggestion Skill

## Descrizione
Agent specializzato nell'interpretare descrizioni in linguaggio naturale e generare query SQL o piani di estrazione dati ottimali. Apprende dalle query passate e dai loro risultati.

## Capabilities
- Interpretare descrizioni naturali di analisi dati
- Generare query SQL per Oracle partendo da descrizioni
- Suggerire colonne rilevanti per CSV/Excel
- Apprendere dalle query precedenti di successo
- Riconoscere pattern analitici comuni
- Fornire fallback intelligenti

## System Prompt
Tu sei un esperto di analisi dati e SQL Oracle. La tua specialità è comprendere cosa l'utente vuole analizzare da una semplice descrizione in linguaggio naturale e suggerire il modo più efficiente per estrarre i dati.

Quando l'utente descrive un'analisi:
1. **Comprendi l'obiettivo**: Che KPI cerca? Quali confronti desidera?
2. **Suggerisci la query ottimale**: Se è Oracle, genera SELECT ben formattato
3. **Per CSV/Excel**: Identifica le colonne chiave necessarie
4. **Spiega il piano**: Comunica al tuo agente cosa farai
5. **Mantieni sicurezza**: Solo SELECT/WITH, nessun INSERT/UPDATE/DELETE

## Constraints
- Accettare SOLO query SELECT o WITH per Oracle (read-only)
- Non suggerire operazioni DDL (DROP, CREATE, ALTER)
- Non eseguire query mutative anche se richieste
- Se incerto sulla fonte dati, chiedere chiarimenti
- Mantenere query efficienti

## Examples

### Esempio 1: Oracle Query
**Input**: "Analizza i top 5 clienti che hanno speso più soldi quest'anno"
**Output**: 
```sql
SELECT 
    c.customer_id,
    c.customer_name,
    SUM(o.order_amount) as total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE EXTRACT(YEAR FROM o.order_date) = EXTRACT(YEAR FROM SYSDATE)
GROUP BY c.customer_id, c.customer_name
ORDER BY total_spent DESC
FETCH FIRST 5 ROWS ONLY;
```

### Esempio 2: CSV Columns
**Input**: "Voglio vedere le vendite per regione nel tempo"
**Output**: 
```
- regione (ragguppamento)
- data_vendita (temporale)
- importo_vendita (valore)
```
"""
    
    def process(self, context: AgentContext) -> AgentContext:
        """
        Processo:
        1. Legge user_input (descrizione naturale dell'analisi)
        2. Consulta history per query simili
        3. Se trova match buoni, suggerisce query storica
        4. Altrimenti, genera nuova query con LLM
        5. Salva il suggerimento nel context
        """
        self.log(f"Analizzando: {context.user_input[:50]}...")
        
        try:
            # Estrai tipo sorgente dal metadata
            source_type = context.metadata.get("source_type", "oracle")
            
            # 1️⃣ Consulta history per query simili
            similar_queries = self.history_manager.find_similar_queries(
                description=context.user_input,
                source_type=source_type,
                similarity_threshold=0.6
            )
            
            if similar_queries:
                # Usa la query migliore dalla history
                best_match = similar_queries[0]
                self.log(f"✅ Trovata query simile (somiglianza: {best_match['similarity']:.1%})")
                
                suggestion = {
                    "source": "history",
                    "query": best_match['query'],
                    "description": best_match['description'],
                    "similarity": best_match['similarity'],
                    "feedback_score": best_match['feedback_score'],
                    "query_id": best_match['id'],
                    "reason": f"Query simile usata {best_match['execution_count']} volte con successo {best_match['success_count']} volte"
                }
            else:
                # 2️⃣ Genera nuova query con LLM
                self.log("Nessuna query storica simile trovata, genero una nuova...")
                suggestion = self._generate_new_query(context, source_type)
            
            # 3️⃣ Salva il suggerimento nel context
            context.raw_data["extraction_suggestion"] = suggestion
            context.raw_data["suggestion_source"] = suggestion.get("source", "generated")
            
            self.log(f"✅ Suggerimento preparato ({suggestion.get('source', 'unknown')})")
            
        except Exception as e:
            context.add_error(str(e), agent=self.name)
            self.log(f"❌ Errore: {e}")
        
        return context
    
    def _generate_new_query(self, context: AgentContext, source_type: str) -> dict:
        """
        Genera una nuova query usando LLM.
        Ritorna dict con query e metadata.
        """
        try:
            # Prepara le istruzioni in base al tipo sorgente
            if source_type == "oracle":
                instructions = self._get_oracle_instructions(context)
            elif source_type in ["csv", "excel"]:
                instructions = self._get_csv_instructions(context)
            else:
                instructions = self._get_generic_instructions(context)
            
            # Chiama LLM
            messages = [{"role": "user", "content": instructions}]
            response = self.call_openai(messages, temperature=0.5)
            
            # Parsifica risposta (dovrebbe contenere JSON)
            suggestion = self._parse_llm_response(response, source_type)
            
            # Salva la nuova query nella history per apprendimento futuro
            try:
                query_text = suggestion.get("query", "")
                if query_text:
                    query_id = self.history_manager.add_query(
                        description=context.user_input,
                        query_text=query_text,
                        source_type=source_type,
                        notes=f"Generata automaticamente per: {context.user_input[:100]}"
                    )
                    suggestion["query_id"] = query_id
                    suggestion["saved_to_history"] = True
            except Exception as e:
                self.logger.warning(f"Impossibile salvare query in history: {e}")
            
            return suggestion
        
        except Exception as e:
            self.logger.error(f"Errore generazione query: {e}")
            raise
    
    def _get_oracle_instructions(self, context: AgentContext) -> str:
        """Istruzioni per generare query Oracle"""
        return f"""
Tu sei un esperto di Oracle SQL. L'utente vuole fare questa analisi:
"{context.user_input}"

GENERA una query SQL Oracle che soddisfi questa richiesta.

REGOLE RIGOROSE:
- SOLO SELECT o WITH (read-only, no INSERT/UPDATE/DELETE/DDL)
- Query ben formattata con indentazione
- Commenti se query complessa
- Usa FETCH FIRST N ROWS ONLY per limitare risultati
- Presumi tabelle standard (customers, orders, products, ecc.)

RISPOSTA IN QUESTO FORMATO (JSON):
{{
    "query": "SELECT ... FROM ... WHERE ...",
    "description": "Breve spiegazione della query in italiano",
    "tables_used": ["customers", "orders"],
    "columns_extracted": ["customer_id", "order_amount", "order_date"],
    "complexity": "simple" | "medium" | "complex"
}}
"""
    
    def _get_csv_instructions(self, context: AgentContext) -> str:
        """Istruzioni per suggerire colonne da CSV/Excel"""
        return f"""
L'utente ha caricato un file CSV/Excel e vuole fare questa analisi:
"{context.user_input}"

SUGGERISCI le colonne principali da usare per questa analisi.

RISPOSTA IN QUESTO FORMATO (JSON):
{{
    "main_columns": ["colonna1", "colonna2"],
    "grouping_column": "colonna_per_raggruppamento",
    "value_column": "colonna_numerica",
    "time_column": "colonna_temporale_se_presente",
    "description": "Breve spiegazione dell'analisi consigliata in italiano",
    "chart_suggestions": ["bar", "line", "scatter"]
}}
"""
    
    def _get_generic_instructions(self, context: AgentContext) -> str:
        """Istruzioni generiche"""
        return f"""
Suggerisci un piano di estrazione dati per questa richiesta:
"{context.user_input}"

RISPOSTA IN FORMATO JSON con questi campi:
{{
    "source": "oracle|csv|excel",
    "query": "...",
    "description": "Spiegazione in italiano",
    "steps": ["passo1", "passo2"]
}}
"""
    
    def _parse_llm_response(self, response: str, source_type: str) -> dict:
        """
        Parsifica la risposta LLM.
        Estrae JSON dalla risposta anche se c'è testo aggiuntivo.
        """
        try:
            # Tenta di trovare JSON nella risposta
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                parsed["source"] = "generated"
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: crea risposta con il testo completo
        return {
            "source": "generated",
            "query": response,
            "description": "Query generata da LLM",
            "raw_response": response
        }
