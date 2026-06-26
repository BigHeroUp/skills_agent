# My Skill Agent - Senior AI Data Analyst

Sistema agentico locale per analisi dati deterministiche, sessioni iterative,
conoscenza analitica riusabile e report professionali. OpenAI e un supporto
opzionale per interpretazione e stile, non la fonte dei risultati numerici.

Memoria tecnica, stato corrente e roadmap:
[PROJECT_STATUS.md](PROJECT_STATUS.md).

## Architettura

```text
Input: richiesta + CSV / Excel / Oracle
    |
    v
[Analysis Session Manager]
    |
    v
[Pattern Knowledge Engine]
    |
    v
[Learning Engine]
    |
    v
[Analytical Reasoning Layer]
    |
    v
[Advanced Statistical Engine]
    |
    v
[Anomaly Detection Engine]
    |
    v
[Analysis Engine / Autonomous Analyst]
    |
    v
[Senior Data Analyst Engine]
    |
    v
Report locale + grafici + PDF + follow-up
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
- Sessioni iterative con classificazione locale delle richieste.
- Riconoscimento di pattern analitici e suggerimento automatico delle analisi.
- Domain Intelligence Packs locali per arricchire pattern, KPI, domande e
  report senza modificare il core engine.
- Learning Engine locale per confidence, promozione e declassamento pattern.
- Analytical Reasoning Layer locale per ordinare analisi, esclusioni e chiarimenti.
- Advanced Statistical Engine locale per percentili, dispersione, outlier,
  trend, soglie, correlazioni e completezza.
- Anomaly Detection Engine locale per outlier, spike, degrado, drift e SLA.
- Calcoli deterministici Python/Pandas.
- Insight e report locali da `SeniorDataAnalystEngine`.
- Grafici Plotly generati dal dataframe reale.
- Report professionale in italiano prodotto anche senza OpenAI.
- Arricchimento linguistico OpenAI opzionale.
- Logging applicativo con rotazione in `logs/app.log`.
- Storico locale di query e pattern in SQLite.

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
|-- PROJECT_STATUS.md
|-- domain_packs/
|   |-- README.md
|   `-- telepedaggio/
|       |-- domain_pack.yaml
|       |-- patterns.json
|       |-- kpi_definitions.json
|       |-- strategy_rules.json
|       |-- questions.json
|       |-- terminology.json
|       `-- report_template.md
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
|   |-- analysis_engine.py
|   |-- advanced_statistical_engine.py
|   |-- anomaly_detection_engine.py
|   |-- analysis_session_manager.py
|   |-- autonomous_analyst.py
|   |-- analytical_reasoning_layer.py
|   |-- domain_pack_loader.py
|   |-- learning_engine.py
|   |-- pattern_knowledge_engine.py
|   |-- semantic_memory.py
|   |-- senior_data_analyst_engine.py
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
- `services/analytical_reasoning_layer.py` costruisce la strategia analitica
  locale ordinata, con razionale, analisi escluse e domande di chiarimento.
- `services/advanced_statistical_engine.py` calcola statistiche avanzate locali
  JSON-serializzabili con pandas/numpy.
- `services/anomaly_detection_engine.py` rileva anomalie spiegabili, severity,
  confidence, drift, degrado e violazioni SLA senza OpenAI.
- `services/domain_pack_loader.py` scopre e carica conoscenza di dominio locale
  da `domain_packs/`, senza chiamate OpenAI e senza dipendenze pesanti.
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

4. Facoltativo: inserisci nel file `.env` una chiave OpenAI valida per le
   funzioni linguistiche che non dispongono ancora di fallback completo.

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
| 6 | `AnalystAgent` | Genera insight locali e arricchimento LLM opzionale | `insights`, `local_analysis` |
| 7 | `ReportGeneratorAgent` | Produce sempre il report locale finale | `final_report` |

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

## Milestone intermedia: Analytical Reasoning Layer

`services/analytical_reasoning_layer.py` introduce un livello locale di
ragionamento analitico senza chiamate OpenAI. Il motore legge richiesta utente,
metadata del dataframe, pattern rilevati dal `PatternKnowledgeEngine` e
`learning_state`, poi produce una strategia JSON-serializzabile con:

- `recommended_sequence`, cioe analisi ordinate con priorita, colonne richieste,
  dipendenze, output atteso, razionale e confidence;
- `excluded_analyses`, con motivo esplicito quando i dati non consentono trend,
  statistiche numeriche o segmentazioni;
- `clarification_questions`, per richieste ambigue o soglie/SLA non definite;
- `reasoning_trace`, audit trail delle decisioni e dei fattori di ranking;
- `data_requirements` e `stopping_conditions`.

Regole principali:

- non vengono inventate colonne non presenti nei metadata;
- senza colonne data/ora non vengono suggeriti trend temporali;
- senza colonne numeriche non vengono suggerite statistiche numeriche,
  percentili, outlier o confronti soglia;
- richieste su tempi, performance o SLA danno priorita a percentili, trend,
  outlier e soglie quando i dati lo consentono;
- richieste su distribuzioni o categorie danno priorita a segmentazioni e top
  valori.

L'integrazione corrente salva `analytical_strategy` e
`analytical_reasoning_trace` in `AgentContext`, `processed_data` e nelle
iterazioni dell'`AnalysisSessionManager`. Il `SeniorDataAnalystEngine` include
nel report la sezione "Strategia analitica adottata".

## Milestone 7: Advanced Statistical Engine

`services/advanced_statistical_engine.py` introduce una libreria statistica
locale senza OpenAI. Il motore usa solo pandas/numpy e produce output
JSON-serializzabili anche quando il dataframe e vuoto o una colonna non e
compatibile.

Analisi supportate:

- statistiche descrittive e percentili P10, P25, P50, P75, P90, P95, P99;
- dispersione: range, IQR, varianza, deviazione standard, coefficiente di
  variazione e MAD;
- outlier detection con metodo IQR, z-score e modified z-score;
- trend temporali con rolling mean, rolling standard deviation, growth percent
  e month-over-month;
- confronto soglie/SLA;
- matrici di correlazione Pearson, Spearman e Kendall quando applicabili;
- frequency table per colonne categoriali;
- analisi missing/completeness.

Integrazione corrente:

- il `DataProcessorAgent` esegue il motore quando strategy, pattern o metadata
  indicano analisi statistiche utili;
- l'`AnalyticalReasoningLayer` suggerisce dispersione avanzata e correlation
  matrix quando il dataset lo consente;
- il `PatternKnowledgeEngine` arricchisce `time_performance_analysis` con
  metriche robuste e outlier avanzati;
- il `SeniorDataAnalystEngine` include nel report percentili, IQR/MAD, outlier,
  soglie e correlazioni quando presenti;
- `AgentContext` e `processed_data` espongono `advanced_statistical_results`.

## Milestone 8: Anomaly Detection Engine

`services/anomaly_detection_engine.py` introduce un motore locale per rilevare
anomalie statistiche e segnali di degrado usando pandas/numpy e, dove utile,
`AdvancedStatisticalEngine`.

Il motore rileva:

- outlier numerici;
- spike temporali e cambi improvvisi;
- degrado prestazionale su finestre recenti rispetto a baseline storica;
- drift rispetto a risultati statistici baseline;
- possibili violazioni soglia/SLA;
- severita (`low`, `medium`, `high`, `critical`) e `confidence_score`.

Ogni anomalia espone `anomaly_id`, tipo, colonna interessata, periodo quando
disponibile, valore osservato, valore atteso, deviazione, evidenza, metodo e
raccomandazione.

Integrazione corrente:

- il `DataProcessorAgent` esegue anomaly detection quando strategy, pattern o
  richiesta utente indicano outlier, anomalie, spike, degrado, drift, soglie o
  SLA;
- l'`AnalyticalReasoningLayer` suggerisce `anomaly_detection` quando i dati lo
  consentono;
- l'`AnalysisSessionManager` salva `anomaly_detection_results` per ogni
  iterazione;
- il `SeniorDataAnalystEngine` include nel report la sezione "Anomalie
  rilevate";
- `AgentContext` e `processed_data` espongono `anomaly_detection_results`.

## Milestone 9: Domain Intelligence Packs Architecture

`services/domain_pack_loader.py` introduce una architettura locale per caricare
conoscenza di dominio senza modificare il core engine. Ogni pack contiene
manifest, pattern, KPI, regole strategiche, domande di chiarimento, terminologia
e template report.

Il pack iniziale `domain_packs/telepedaggio` copre:

- contratti, sottoscrizioni, attivazioni, device/OBU e antenne;
- consegne a mano, corriere e agenzia;
- tempi di attivazione, percentili, SLA e degrado temporale;
- anomalie per metodo consegna e coerenza stato antenna/contratto.

Il `DataProcessorAgent` suggerisce il pack piu coerente con richiesta utente e
metadata del dataframe, salva `domain_pack_context` nel context e nei
`processed_data`, e passa tale contesto a:

- `PatternKnowledgeEngine`, per arricchire metriche, grafici e step suggeriti;
- `AnalyticalReasoningLayer`, per usare regole strategiche e domande di dominio;
- `SeniorDataAnalystEngine`, per includere nel report la sezione
  "Dominio riconosciuto".

Il sistema non blocca la pipeline se nessun pack viene trovato.

## Senior Data Analyst Engine locale

`services/senior_data_analyst_engine.py` riduce la dipendenza da OpenAI
trasformando i risultati deterministici gia calcolati in una relazione
professionale. Il motore non accede al dataframe e non chiama servizi esterni:
usa esclusivamente `deterministic_summary`, `deterministic_results`,
`execution_summary`, `analysis_plan` e gli eventuali risultati multi-step
dell'`AutonomousAnalyst`.

L'output JSON-serializzabile include:

- riepilogo esecutivo;
- evidenze principali;
- KPI numerici;
- trend temporali;
- anomalie ed estremi potenziali;
- segmentazioni;
- note sulla qualita dei dati;
- raccomandazioni operative;
- report finale in Markdown.

`AnalystAgent` esegue sempre prima il motore locale. `ReportGeneratorAgent`
considera il report locale come fonte primaria. Se `OPENAI_API_KEY` e
configurata, OpenAI puo aggiungere un arricchimento narrativo; se la chiave
manca o la chiamata fallisce, insight e report finale vengono comunque
prodotti senza modificare i risultati deterministici.

## Milestone 4: Analysis Session Manager - Completata

`services/analysis_session_manager.py` introduce una memoria locale delle
sessioni analitiche senza chiamate OpenAI. Ogni sessione conserva:

- richiesta iniziale;
- tipo sorgente;
- metadata del dataframe;
- timestamp di creazione e aggiornamento;
- iterazioni analitiche numerate.

Ogni iterazione contiene prompt utente, tipo richiesta, piano analitico,
risultati deterministici, insight e snapshot del report finale.

La classificazione locale distingue:

- `initial_analysis`;
- `refinement`;
- `segmentation_request`;
- `time_window_request`;
- `threshold_comparison`;
- `anomaly_deep_dive`.

Il manager puo costruire il contesto per l'iterazione successiva ed esportare
una sintesi JSON-serializzabile. Lo storage e attualmente in memoria Python,
con una struttura versionata pronta per una futura implementazione SQLite.

## Milestone 5: Pattern Knowledge Engine - Completata

`services/pattern_knowledge_engine.py` introduce una Knowledge Base analitica
locale e versionata. Il motore associa la richiesta utente a pattern ricorrenti
e suggerisce metriche, raggruppamenti, grafici e step di approfondimento senza
chiamare OpenAI.

I pattern iniziali sono:

- `time_performance_analysis`: media, mediana, percentili, trend, outlier,
  soglie/SLA e degrado;
- `categorical_segmentation`: distribuzioni, top valori, confronto e anomalie
  tra segmenti;
- `data_quality_audit`: null, duplicati, formati, incoerenze e colonne
  critiche;
- `operational_kpi_analysis`: KPI, distribuzioni, trend e raccomandazioni
  operative.

L'integrazione corrente:

- arricchisce `analysis_plan` nel `DataProcessorAgent` dopo l'esecuzione
  deterministica;
- salva i pattern rilevati in ogni iterazione
  dell'`AnalysisSessionManager`;
- aggiunge note metodologiche e raccomandazioni basate sui pattern nel
  `SeniorDataAnalystEngine`;
- espone catalogo e payload in formato JSON-serializzabile, pronto per una
  futura persistenza SQLite.

Gli step suggeriti rappresentano best practice raccomandate. Non vengono
presentati come risultati eseguiti finche il relativo motore deterministico non
ha calcolato le metriche.

## Milestone 6: Learning Engine - Completata

`services/learning_engine.py` introduce un ciclo locale di apprendimento sui
pattern analitici senza chiamate OpenAI. Il motore registra eventi di utilizzo e
feedback, aggiorna `confidence_score`, promuove pattern efficaci, declassa
pattern poco utili e produce raccomandazioni operative per migliorare la
Knowledge Base.

Il motore espone payload JSON-serializzabili e pronti per una futura persistenza
SQLite:

- `record_usage()`: registra l'uso di un pattern;
- `record_feedback()`: applica feedback utile, non utile o neutro;
- `update_confidence()`: ricalcola affidabilita e stato del pattern;
- `recommend_patterns()`: ordina i pattern disponibili per confidence appresa;
- `export_learning_state()`: esporta statistiche, eventi e audit trail.

Integrazione corrente:

- `PatternKnowledgeEngine` puo ricevere `learning_state` e usarlo per ordinare i
  pattern rilevati;
- `AnalysisSessionManager` salva `learning_events` e snapshot di
  `learning_state` per ogni iterazione;
- `SeniorDataAnalystEngine` include nel report note su pattern promossi o
  declassati;
- `AgentContext` e `processed_data` espongono `learning_state` e
  `learning_events`.

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

- Gli agenti precedenti all'analisi possono ancora usare OpenAI per
  interpretazione e preparazione; insight e report finale hanno invece un
  percorso locale completo.
- Lo stato runtime della dashboard e centralizzato in memoria di processo e non
  e pensato per deployment multiutente o multi-worker.

## Repository

Repository GitHub:

```text
https://github.com/BigHeroUp/skills_agent
```
