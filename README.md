# My Skill Agent 🤖 - Multi-Agent Hub & Spoke

Un sistema avanzato di agenti OpenAI che lavorano insieme in un'architettura Hub & Spoke.

## 🏗️ Architettura

5 agenti specializzati che lavorano in sequenza, passandosi un **context condiviso**:

```
Input Utente
    ↓
[Hub - Coordinatore]
    ├→ DataExtractor    (estrae dati)
    ├→ DataValidator    (valida dati)
    ├→ DataProcessor    (elabora dati)
    ├→ Analyst          (analizza)
    └→ ReportGenerator  (crea report)
    ↓
Output Finale
```

## 📁 Struttura

```
my_skill_agent/
├── main.py                 # Entry point principale
├── coordinator.py          # Orizzazione del flusso
├── requirements.txt        # Dipendenze
├── .env.template           # Template configurazione
├── agents/
│   ├── base_agent.py      # Classe base (tutti gli agenti ereditano)
│   ├── data_extractor.py  # Estrae dati
│   ├── data_validator.py  # Valida dati
│   ├── data_processor.py  # Elabora dati
│   ├── analyst.py         # Analizza dati
│   └── report_generator.py # Genera report
├── utils/
│   ├── context.py         # AgentContext condiviso
│   └── __init__.py
└── skills/
    ├── oracle_sql/SKILL.md
    ├── email_writer/SKILL.md
    └── ...
```

## 🚀 Setup

1. **Installa dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configura API key:**
   ```bash
   copy .env.template .env
   # Edita .env e aggiungi: OPENAI_API_KEY=sk-...
   ```

3. **Esegui il sistema:**
   ```bash
   python main.py
   ```

## 🤖 I 7 Agenti (Nuovo: QuerySuggestion!)

| # | Agente | Compito | Input | Output |
|---|--------|--------|-------|--------|
| 0 | **DataSourceManager** | Carica dati dalla fonte | metadata sorgente | raw_data con dataframe |
| 1 | **QuerySuggestion** 🆕 | **Suggerisce query da descrizione naturale** | **user_input + source_type** | **extraction_suggestion** |
| 2 | **DataExtractor** | Estrae dati usando il suggerimento | Richiesta utente | extraction_plan |
| 3 | **DataValidator** | Valida i dati | raw_data | validation_results |
| 4 | **DataProcessor** | Elabora e trasforma | raw_data validato | processed_data |
| 5 | **Analyst** | Genera insight | processed_data | insights |
| 6 | **ReportGenerator** | Crea report | insights + processed_data | final_report |

## 🔄 Flusso di Comunicazione

Gli agenti comunicano tramite un **AgentContext** condiviso:

```python
context = {
    'user_input': str,           # Input originale
    'raw_data': dict,            # Dati estratti
    'validation_results': dict,  # Risultati validazione
    'processed_data': dict,      # Dati elaborati
    'insights': dict,            # Analisi e insight
    'final_report': str,         # Report finale
    'errors': list,              # Errori accumulati
}
```

## 🧠 QuerySuggestionAgent - Learning da Descrizioni Naturali (NUOVO!)

**Risolve il problema**: Utenti non esperti non devono più scrivere query SQL o selezionare colonne manualmente.

### Come Funziona

1. **Input**: L'utente scrive solo una descrizione naturale dell'analisi
   - Es: "Analizza i top 5 clienti per volume di ordini"
   - Es: "Mostra le vendite per regione nel tempo"

2. **Query Suggestion Agent**:
   - Consulta una **storia di query apprese** (SQLite in `data/query_history.db`)
   - Se trova una query simile con buon score → la suggerisce
   - Altrimenti → genera una nuova query con LLM (Oracle SQL o CSV columns)

3. **Learning Automatico**:
   - Ogni query viene memorizzata con la descrizione utente
   - Dopo l'analisi, il sistema registra se la query ha dato buoni risultati
   - Query di successo ricevono uno score più alto
   - Le volte successive, query simili vengono suggerite automaticamente

4. **Output**: `extraction_suggestion` nel context
   - Contiene la query/piano ottimale
   - Include metadati (source, similarity score, success count)

### Database di Learning

```
data/query_history.db
├── query_history table
│   ├── id, description, query_text
│   ├── source_type (oracle|csv|excel)
│   ├── feedback_score (0-1)
│   ├── execution_count, success_count
│   └── created_at, last_used
```

### Skill Utilisé

- **`skills/query_suggestion/SKILL.md`**: Istruzioni LLM per generare query da descrizioni naturali
- **`utils/query_history_manager.py`**: Gestione SQLite della storia

## 💡 Come Aggiungere un Nuovo Agente

1. Crea un file in `agents/nuovo_agent.py`:
```python
from agents.base_agent import BaseAgent
from utils.context import AgentContext

class NuovoAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="NuovoAgent", skill_name="nuovo_skill")
    
    def process(self, context: AgentContext) -> AgentContext:
        # Elabora il context
        return context
```

2. Aggiungi a `coordinator.py` nella lista `self.agents`

3. Crea il file `skills/nuovo_skill/SKILL.md` con la descrizione

## 🧪 Test

Per testare il sistema, esegui:
```bash
python main.py
# Scegli opzione 1 e descrivi una task di analisi dati
```

Esempio: "Analizza i clienti top per volume di ordini"

### Test del QuerySuggestionAgent (senza UI)

```bash
python test_integration.py
```

Output atteso:
```
✅ TUTTI I TEST PASSATI - Sistema pronto!
```

Questo test verifica:
- ✓ Import di tutti i moduli
- ✓ Pipeline con QuerySuggestionAgent incluso
- ✓ Generazione di suggerimenti per CSV
- ✓ Generazione di suggerimenti per Oracle
- ✓ Funzionamento di QueryHistoryManager
- ✓ Creazione di SKILL.md

## 📊 Esempio di Output

```
🚀 INIZIO ELABORAZIONE MULTI-AGENT
============================================================

→ Esecuzione: DataSourceManager
🤖 [DataSourceManager] Caricamento dati da fonte...
🤖 [DataSourceManager] ✅ Dati caricati con successo

→ Esecuzione: QuerySuggestion (NUOVO!)
🤖 [QuerySuggestion] Analizzando: Analizza i clienti top...
🤖 [QuerySuggestion] ✅ Trovata query simile (somiglianza: 82%)
🤖 [QuerySuggestion] Suggerimento: SELECT TOP 5 customers BY order_volume

→ Esecuzione: DataExtractor
🤖 [DataExtractor] Estrazione dati da: Analizza i clienti top...
🤖 [DataExtractor] ✅ Dati estratti con successo

→ Esecuzione: DataValidator
🤖 [DataValidator] Validazione dati in corso...
🤖 [DataValidator] ✅ Validazione completata

→ Esecuzione: DataProcessor
🤖 [DataProcessor] Elaborazione dati...
🤖 [DataProcessor] ✅ Elaborazione completata

→ Esecuzione: Analyst
🤖 [Analyst] Analisi in corso...
🤖 [Analyst] ✅ Insight generati

→ Esecuzione: ReportGenerator
🤖 [ReportGenerator] Generazione report finale...
🤖 [ReportGenerator] ✅ Report generato

✅ ELABORAZIONE COMPLETATA
============================================================
```

## 🔗 Pattern: Sequential Relay

Ogni agente:
1. **Legge** il context
2. **Elabora** i dati
3. **Aggiorna** il context
4. **Passa** al prossimo agente

Vantaggi:
- ✅ Semplice da capire e debuggare
- ✅ Facile aggiungere/rimuovere agenti
- ✅ Tutto tracciabile
- ✅ Error handling robusto

## 📝 Requisiti

- Python 3.8+
- OpenAI API key
- Librerie: openai, python-dotenv

## Log applicativi

L'applicazione scrive gli eventi operativi in `logs/app.log`, con rotazione automatica
quando il file raggiunge 2 MB e conservazione degli ultimi 5 archivi.

Sono registrati avvio applicazione, upload, test connessione Oracle, avanzamento
della pipeline, chiamate OpenAI ed errori tecnici. Password e testo delle query
Oracle non vengono registrati.

Per seguire i log in PowerShell durante l'esecuzione:

```powershell
Get-Content .\logs\app.log -Encoding UTF8 -Wait
```

