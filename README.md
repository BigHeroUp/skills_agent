# My Skill Agent - Multi-Agent Hub & Spoke

Dashboard locale di analisi dati assistita da LLM, costruita con una pipeline di
agenti specializzati che lavorano in sequenza su un contesto condiviso.

## Architettura

```text
Input utente
    |
    v
[Hub - Coordinator]
    |-> DataSourceManager  carica dati da CSV, Excel o Oracle
    |-> QuerySuggestion    suggerisce query o colonne da descrizione naturale
    |-> DataExtractor      prepara il piano di estrazione
    |-> DataValidator      valida i dati
    |-> DataProcessor      elabora il contenuto
    |-> Analyst            genera insight
    |-> ReportGenerator    crea il report finale
    |
    v
Output finale
```

La dashboard viene eseguita in locale con Dash su:

```text
http://localhost:8050/
```

## Funzionalita

- Upload e analisi di file CSV.
- Upload e analisi di file Excel.
- Connessione read-only a database Oracle.
- Descrizione dell'analisi in linguaggio naturale.
- Suggerimento automatico di query o colonne tramite `QuerySuggestionAgent`.
- Grafici Plotly generati dal dataframe reale.
- Report testuale in italiano generato tramite OpenAI.
- Logging applicativo con rotazione in `logs/app.log`.
- Storico locale delle query apprese in SQLite.

## Struttura del progetto

```text
my_skill_agent/
|-- main.py
|-- app_dash.py
|-- coordinator.py
|-- requirements.txt
|-- WORKING_CONTEXT.md
|-- CAPABILITIES.md
|-- APPLICATION_CONTEXT.md
|-- IMPLEMENTATION_SUMMARY.md
|-- agents/
|   |-- base_agent.py
|   |-- data_source_manager.py
|   |-- query_suggestion_agent.py
|   |-- data_extractor.py
|   |-- data_validator.py
|   |-- data_processor.py
|   |-- analyst.py
|   `-- report_generator.py
|-- connectors/
|   `-- data_connectors.py
|-- services/
|   |-- analysis_service.py
|   `-- oracle_service.py
|-- ui/
|   |-- callbacks.py
|   `-- layout.py
|-- utils/
|   |-- context.py
|   |-- data_analysis.py
|   |-- oracle_query_validator.py
|   |-- chart_generator.py
|   |-- logging_config.py
|   |-- pdf_generator.py
|   `-- query_history_manager.py
|-- skills/
|   |-- oracle_sql/SKILL.md
|   |-- email_writer/SKILL.md
|   |-- query_suggestion/SKILL.md
|   `-- conversation/SKILL.md
`-- tests/
```

La dashboard Dash e organizzata in tre layer:

- `app_dash.py` inizializza l'app, collega layout e callback, e mantiene solo
  wrapper di compatibilita per i test esistenti.
- `ui/layout.py` contiene CSS/template Dash e albero dei componenti UI.
- `ui/callbacks.py` registra le callback Dash e delega la logica applicativa ai
  service.
- `services/analysis_service.py` centralizza stato runtime, parsing upload
  CSV/Excel, invocazione pipeline multi-agent e analisi follow-up deterministiche.
- `services/oracle_service.py` incapsula il test di connessione Oracle senza
  esporre la password allo store browser.

Nota: i test attuali sono script nella root del progetto:

- `test_new_modules.py`
- `test_integration.py`

## Setup

1. Crea o attiva un ambiente virtuale Python.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Installa le dipendenze.

```powershell
pip install -r requirements.txt
```

3. Crea il file `.env` partendo dal template.

```powershell
copy .env.template .env
```

4. Inserisci nel file `.env` una chiave OpenAI valida.

```text
OPENAI_API_KEY=sk-...
```

5. Avvia l'applicazione.

```powershell
python main.py
```

## Agenti della pipeline

| Ordine | Agente | Responsabilita | Output principale |
| --- | --- | --- | --- |
| 1 | `DataSourceManagerAgent` | Carica dati da CSV, Excel o Oracle | `raw_data` |
| 2 | `QuerySuggestionAgent` | Suggerisce query o colonne da descrizione naturale | `extraction_suggestion` |
| 3 | `DataExtractorAgent` | Prepara il piano di estrazione | `extraction_plan` |
| 4 | `DataValidatorAgent` | Valida i dati caricati | `validation_results`, `is_valid` |
| 5 | `DataProcessorAgent` | Elabora i dati validati | `processed_data`, `deterministic_summary` |
| 6 | `AnalystAgent` | Genera insight | `insights`, `deterministic_insights` |
| 7 | `ReportGeneratorAgent` | Produce il report finale | `final_report` |

Gli agenti leggono e aggiornano la stessa istanza di `AgentContext`.

Ogni agente LLM include nel prompt le istruzioni della propria skill tramite
`BaseAgent.build_prompt_with_skill()`. Le regole operative possono quindi essere
aggiornate nei file `skills/*/SKILL.md` senza riscrivere il codice Python.

## QuerySuggestionAgent

Il `QuerySuggestionAgent` consente all'utente di descrivere l'analisi in
linguaggio naturale senza scrivere manualmente SQL o selezionare colonne.

Esempi:

- "Analizza i top 5 clienti per volume di ordini"
- "Mostra le vendite per regione nel tempo"
- "Trova anomalie negli importi mensili"

Il funzionamento e il seguente:

1. legge `user_input` e `source_type`;
2. cerca query simili in `data/query_history.db`;
3. se trova un match sopra soglia, riusa la query storica;
4. se non trova match, genera una nuova query o un piano con LLM;
5. salva il suggerimento nel contesto.

Il database SQLite contiene la tabella `query_history` con descrizione, query,
tipo sorgente, score di feedback, contatori di utilizzo e timestamp.

## Oracle

La connessione Oracle e gestita in modalita read-only.

Sono consentite solo query che iniziano con:

- `SELECT`
- `WITH`

Non sono consentite query mutative o DDL come:

- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `CREATE`
- `ALTER`

Le credenziali non devono essere salvate nei log o nei file versionati.

La validazione delle query Oracle e centralizzata in
`utils/oracle_query_validator.py`, usata sia dal source manager sia dal
connettore Oracle.

## Quality gate Git

E disponibile un hook pre-commit opzionale in `.githooks/pre-commit`.

Per abilitarlo:

```powershell
.\scripts\install_git_hooks.ps1
```

Da quel momento Git esegue `.\scripts\verify.ps1` prima di ogni commit.

## Grafici

`utils/chart_generator.py` genera automaticamente grafici Plotly dal dataframe:

- istogrammi per colonne numeriche;
- heatmap di correlazione;
- top valori per colonne categoriche;
- serie temporali se esistono colonne data/ora;
- box plot per anomalie;
- tabella di statistiche descrittive.

Quando la descrizione utente richiede esplicitamente grafici riconoscibili, il
sistema li genera prima dei grafici automatici. Per esempio:

- grafico a colonne con occorrenze degli stati/status ticket;
- grafico temporale dell'andamento della lavorazione ticket, se esiste una
  colonna data/ora utilizzabile.

## Test

Esegui i test principali con:

```powershell
python test_new_modules.py
python test_integration.py
```

`test_new_modules.py` verifica import e moduli singoli.

`test_integration.py` verifica l'integrazione della pipeline con
`QuerySuggestionAgent` e `QueryHistoryManager`.

La suite pytest principale e in `tests/`:

```powershell
python -m pytest
```

La verifica completa del progetto e:

```powershell
.\scripts\verify.ps1
```

Lo script esegue compilazione Python, scanner anti-segreti, test pytest e import
della dashboard.

## Feedback query

Dopo il completamento dell'analisi la dashboard mostra un controllo di feedback
per il suggerimento query usato.

L'utente puo indicare se il suggerimento e stato:

- utile;
- non utile.

Il feedback aggiorna `data/query_history.db` tramite
`QueryHistoryManager.update_feedback()`, modificando `execution_count`,
`success_count`, `feedback_score` e `last_used`.

## Analisi deterministica

`utils/data_analysis.py` calcola statistiche direttamente dal dataframe reale.

I risultati deterministici includono:

- numero righe e colonne;
- tipi dato;
- valori mancanti;
- righe duplicate;
- statistiche numeriche;
- top valori categorici;
- correlazioni numeriche principali;
- range temporali per colonne data/ora.

Questi risultati vengono salvati in `processed_data["deterministic_summary"]` e
usati dall'`AnalystAgent` per produrre insight separati dal testo generato dal
modello.

## Milestone 2: Analysis Engine deterministico

La Milestone 2 introduce un layer esplicito per separare interpretazione,
calcolo reale e apprendimento locale:

- l'LLM resta un interprete della richiesta e un generatore di spiegazioni;
- `services/analysis_engine.py` esegue i calcoli reali con Python/Pandas;
- `utils/analysis_history_manager.py` salva pattern analitici riutilizzabili in
  SQLite.

Il modello dati `AnalysisPlan` rappresenta un piano analitico con:

- `analysis_type`;
- `target_column`;
- `group_by_column`;
- `value_column`;
- `time_column`;
- `aggregation`;
- `limit`;
- `description`.

L'`AnalysisEngine` supporta analisi deterministiche JSON-serializzabili:

- conteggio occorrenze per colonna categoriale;
- top N valori per colonna;
- somma, media, minimo e massimo per colonne numeriche;
- trend temporale se esiste una colonna data;
- rilevazione valori nulli;
- rilevazione righe duplicate.

Il `DataProcessorAgent` integra il motore dopo la validazione dei dati e salva
nel context:

- `analysis_plan`;
- `deterministic_results`;
- `execution_summary`.

Gli stessi dati sono anche esposti in `processed_data` per mantenere compatibili
gli agenti successivi, il report e gli export esistenti.

Lo storico locale dei pattern analitici e salvato in:

```text
data/analysis_history.db
```

Quando una nuova richiesta e simile a una richiesta passata con feedback
positivo, il sistema puo riusare il piano analitico precedente e ricalcolare i
risultati sul dataframe corrente. Questo evita che risultati numerici vengano
inventati dal modello: il modello puo proporre o spiegare il piano, ma i valori
finali sono prodotti dal motore deterministico.

## Milestone 2.5: Feedback Engine

La Milestone 2.5 rende operativo il ciclo di apprendimento sui pattern
analitici:

```text
Richiesta utente
    -> AnalysisPlan
    -> AnalysisEngine
    -> deterministic_results
    -> feedback utente
    -> aggiornamento pattern
    -> confidence_score
    -> riuso nelle analisi future
```

Ogni esecuzione dell'`AnalysisEngine` espone nel context e in `processed_data`:

- `analysis_pattern_id`;
- `plan_source`, con valore `new` o `history`;
- `confidence_score`;
- `similarity_score`, quando il piano viene riusato dalla history;
- `similarity_method`, con valore `embedding` o `text`.

Il feedback gia presente in dashboard aggiorna ora due memorie distinte:

- `QueryHistoryManager`, per il suggerimento query esistente;
- `AnalysisHistoryManager`, per il pattern analitico deterministico.

Un pattern nuovo parte con `confidence_score=0.0`. Quando l'utente indica che il
risultato e utile, il sistema aggiorna `execution_count`, `success_count`,
`feedback_score` e ricalcola `confidence_score`. I pattern con feedback basso
non vengono riusati automaticamente.

## Milestone 3: Semantic Memory Engine

La Milestone 3 estende `AnalysisHistoryManager` con una memoria semantica basata
su embeddings. L'obiettivo e riusare pattern non solo quando la richiesta e
simile nel testo, ma quando ha significato simile.

Esempi di richieste che possono convergere sullo stesso pattern:

- "Mostrami i ticket per stato"
- "Distribuzione dei ticket per stato"
- "Quanti ticket ci sono per ogni stato?"
- "Fammi il conteggio delle pratiche per status"

Il modulo `services/semantic_memory.py` gestisce:

- generazione embedding da testo;
- normalizzazione vettori;
- cosine similarity;
- fallback locale a `SequenceMatcher` quando embeddings non sono disponibili.

Il modello embedding non e hardcoded. Si configura con:

```text
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Se la variabile non e valorizzata, il default e:

```text
text-embedding-3-small
```

La chiamata embeddings non e obbligatoria: se `OPENAI_API_KEY` manca, se il
client OpenAI non e disponibile o se la chiamata fallisce, il sistema continua a
funzionare usando la similarita testuale locale.

Lo storico SQLite e migrato in modo compatibile: la colonna `embedding_json`
viene aggiunta se assente e i pattern esistenti restano validi. Quando possibile,
gli embedding mancanti vengono calcolati e salvati al primo riuso.

## Milestone 4: Autonomous Analyst

La Milestone 4 introduce `services/autonomous_analyst.py`, un planner
deterministico multi-step che opera sopra `AnalysisEngine`.

La differenza principale e:

- single-plan analysis: una richiesta specifica produce un solo `AnalysisPlan`;
- autonomous multi-step analysis: una richiesta ampia produce un
  `AutonomousAnalysisPlan` con piu step deterministici.

Esempi di richieste ampie:

- "analizza il dataset";
- "analizza i ticket";
- "fammi un'analisi completa";
- "trova anomalie";
- "dimmi cosa vedi nei dati";
- "fai una panoramica".

In modalita autonoma il sistema puo eseguire:

- distribuzione per colonna categoriale/stato;
- trend temporale se trova una colonna data;
- durata media se trova colonne inizio/fine;
- rilevazione valori nulli;
- rilevazione duplicati;
- top N su colonne categoriali rilevanti;
- aggregazioni numeriche principali.

Il planner non usa nuove chiamate LLM: legge schema, tipi dato e riepilogo
deterministico del dataframe, poi costruisce step Pandas verificabili. I risultati
vengono salvati nel context e in `processed_data`:

- `autonomous_analysis_plan`;
- `autonomous_analysis_results`;
- `autonomous_executive_summary`;
- `autonomous_recommendations`;
- `autonomous_mode`.

## Logging

L'applicazione scrive gli eventi operativi in:

```text
logs/app.log
```

Il log usa rotazione automatica quando il file raggiunge 2 MB e conserva gli
ultimi 5 archivi.

Per seguire il log in PowerShell:

```powershell
Get-Content .\logs\app.log -Encoding UTF8 -Wait
```

## Limiti noti

- Parte dell'analisi testuale e ancora prodotta dall'LLM, ma ora e affiancata da
  statistiche deterministiche calcolate dal dataframe reale.
- Lo stato runtime della dashboard e centralizzato in memoria di processo e non
  e pensato per deployment multiutente o multi-worker.

## Repository

Repository GitHub:

```text
https://github.com/BigHeroUp/skills_agent
```
