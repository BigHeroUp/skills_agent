# Project Status

## Visione del progetto

`skills_agent` non e un semplice tool di analisi dati e non vuole diventare un
chatbot generalista. La visione e costruire un **Senior AI Data Analyst**:
un sistema agentico autonomo che trasformi richieste di business e dati reali
in analisi verificabili, dialoghi utili e decisioni motivate.

Il sistema deve essere capace di:

- acquisire dati da CSV, Excel e Oracle;
- comprendere richieste espresse in linguaggio naturale;
- porre domande di chiarimento quando obiettivi, vincoli o dati sono ambigui;
- ragionare sul problema prima di scegliere le analisi;
- selezionare autonomamente metriche, segmentazioni e controlli;
- costruire ed eseguire analisi statistiche reali sui dati disponibili;
- distinguere sempre interpretazione linguistica e calcolo numerico;
- dialogare con l'utente attraverso iterazioni e analisi successive;
- imparare dalle analisi svolte e dal feedback;
- produrre insight, KPI, trend, anomalie e report professionali di livello
  Senior Data Analyst;
- riusare pattern analitici validati e apprendere dai feedback;
- proporre next best action coerenti con dati, storico e obiettivi;
- ridurre progressivamente, fino a eliminare, la dipendenza obbligatoria dalle
  API OpenAI;
- mantenere tracciabilita, sicurezza e riproducibilita dei risultati.

Il principio architetturale centrale e:

> Un modello linguistico puo interpretare, pianificare o migliorare la forma del
> testo, ma non deve inventare risultati. KPI, statistiche e conclusioni
> fattuali devono derivare da calcoli deterministici o da modelli statistici
> espliciti e verificabili.

## Visione finale

Il prodotto finale deve comportarsi come un Senior AI Data Analyst, non come
un chatbot che risponde genericamente. Deve:

- ragionare su obiettivo, perimetro, qualita e granularita dei dati;
- scegliere autonomamente quali analisi eseguire e in quale ordine;
- spiegare ipotesi, metodi, evidenze e limiti;
- confrontarsi con l'utente per chiarire dubbi e raffinare la richiesta;
- imparare da feedback, correzioni, esiti e pattern efficaci;
- produrre report consulenziali di altissimo livello, con KPI, trend, anomalie,
  raccomandazioni e next best action;
- mantenere risultati numerici riproducibili e auditabili;
- diventare progressivamente indipendente da modelli esterni;
- poter lavorare completamente offline quando tutte le milestone saranno
  completate.

## Stato attuale

### V2 Architecture Foundation

La V2 Architecture Foundation e stata avviata come formalizzazione del progetto
in piattaforma offline-first di Analytical Intelligence.

Punti chiave definiti:

- strategia offline-first esplicita;
- centralita del reasoning deterministico;
- LLM opzionale e non obbligatorio;
- separazione architetturale in macro-layer;
- roadmap V2 e ADR iniziali.

### V2.1.1 Kernel Architecture Foundation

Objective:

- define the future Kernel-Oriented Veraxis architecture;
- formalize the capability-oriented evolution path;
- document the conceptual domain model;
- define development governance for architecture-first growth.

Status:

- completed

Test:

- no runtime feature changes introduced;
- regression verification required through `python3 -m pytest -q`.

### V2.1.2 Kernel Runtime Foundation

Objective:

- introduce the first parallel runtime base for the Veraxis Kernel;
- formalize capabilities, registry, events, memory, and kernel errors;
- keep the current Coordinator pipeline unchanged and stable.

Status:

- completed

Test:

- dedicated kernel runtime tests added;
- full regression suite passed with `224 passed` via `python3 -m pytest -q`.

### V2.1.3 First Kernel Capability Migration

Objective:

- migrate the first real deterministic capability into the Veraxis Kernel;
- expose Knowledge Graph querying through a kernel-native contract;
- keep Coordinator, agents, and dashboard behavior unchanged.

Status:

- completed

Test:

- dedicated capability, bootstrap, and CLI-oriented tests added;
- full regression suite passed with `232 passed` via `python3 -m pytest -q`.

### V2.2.0 Analytical Experience Engine

Objective:

- accumulate deterministic analytical experience from prior analysis runs;
- persist reusable experience locally without storing raw dataframe rows;
- expose offline-first experience refresh and querying through CLI and kernel capability.

Status:

- completed

Test:

- dedicated experience store, builder, engine, query, and kernel capability tests added;
- full regression suite passed with `239 passed` via `python3 -m pytest -q`.

### V2.1.4 Kernel Analytical Parity

Objective:

- expose deterministic categorical analysis through a Kernel-native capability;
- compare Kernel output with the current production analytical engine in shadow mode;
- preserve the Coordinator as the production boundary until broader parity is proven.

Status:

- completed

Test:

- capability bootstrap, validation and semantic cross-tab tests added;
- shadow parity verified for analysis plan, deterministic results and execution summary;
- Redis/RQ test environment restored;
- full regression suite passed with `383 passed` via `python3 -m pytest -q`.

### Validation Lab e Quality Gates

Il progetto ora include `validation_lab/`, una struttura dedicata alla raccolta
di evidenze da test reali e sintetici:

- test case con dataset, prompt, risultato atteso, risultato ottenuto e log;
- quality gate per Data Ingestion, Semantic Understanding, Feature
  Engineering, Intent Planner, Statistical Engine, Root Cause, Report,
  Dashboard UX, LLM Gateway, Learning Engine e Domain Packs;
- template per bug report e architecture review;
- benchmark suite su domini non lavorativi.

La prossima fase deve essere hardening basato su evidenze: prima di introdurre
nuovi engine o nuove feature, i quality gate principali devono essere stabili e
i bug emersi dai test reali devono essere collegati a casi riproducibili.

### Analytical Planning Engine

Questa iterazione introduce l'`AnalyticalPlanningEngine` per pianificare prima
di calcolare:

- parsing deterministico di intent, preprocessing richiesto e follow-up;
- trasformazioni auditabili come `datetime_shift` su colonne data, senza
  sovrascrivere colonne originali;
- quality gate sul KPI `TEMPO_ATTIVAZIONE_GIORNI` con esclusione sicura delle
  durate negative dai KPI principali;
- piani di analisi e visualizzazione limitati e coerenti con la domanda;
- confronto baseline vs subset nelle analisi filtrate successive.

Il Validation Lab include ora
`validation_lab/test_cases/TEST-004_datetime_shift_activation_time.md`, dedicato
al caso GMT `+1h`, uso della colonna adjusted, quality gate sulle durate
negative, report business-first e follow-up comparativo.

### Milestone completate

La cronologia gia integrata in `main` comprende:

1. Refactoring della dashboard Dash in layer UI e service.
2. Analysis Engine deterministico.
3. Feedback Engine per pattern analitici riutilizzabili.
4. Semantic Memory Engine con embeddings opzionali e fallback testuale.
5. Autonomous Analyst deterministico multi-step.
6. Senior Data Analyst Engine locale, integrato su `main` nel commit
   `c23e060`:
   - generazione locale di executive summary;
   - key finding;
   - KPI;
   - trend;
   - segmentazioni;
   - anomalie ed estremi potenziali;
   - note sulla qualita dei dati;
   - raccomandazioni operative;
   - report finale professionale in Markdown;
   - fallback di `AnalystAgent` e `ReportGeneratorAgent` in assenza di OpenAI.
7. **Milestone 4 - Analysis Session Manager**, presente su `main` nel commit
   `a3ab8fd`:
   - classe `AnalysisSessionManager`;
   - sessioni in memoria con struttura versionata;
   - sessioni iterative append-only;
   - classificazione locale delle richieste;
   - contesto per follow-up;
   - export session summary JSON-serializzabile;
   - struttura predisposta per una futura persistenza SQLite.
   - 8 test dedicati.
8. **Milestone 5 - Pattern Knowledge Engine**, completata nel commit locale
   `4f3ad13`:
   - classe `PatternKnowledgeEngine`;
   - quattro pattern analitici iniziali;
   - riconoscimento locale dei pattern da richiesta e metadata;
   - suggerimento automatico di metriche, raggruppamenti, grafici e analisi;
   - arricchimento del piano nel `DataProcessorAgent`;
   - integrazione con `AnalysisSessionManager`;
   - integrazione con `SeniorDataAnalystEngine`;
   - `AgentContext` aggiornato con pattern e step suggeriti;
   - struttura pronta per futura persistenza SQLite;
   - 9 test dedicati.
9. **Milestone 6 - Learning Engine**, completata su branch
   `feature/milestone-6-learning-engine`:
   - classe `LearningEngine`;
   - eventi locali di utilizzo e feedback;
   - aggiornamento progressivo di `confidence_score`;
   - promozione dei pattern efficaci;
   - declassamento dei pattern poco utili;
   - raccomandazioni di miglioramento;
   - audit trail JSON-serializzabile pronto per SQLite;
   - integrazione con `PatternKnowledgeEngine`;
   - integrazione con `AnalysisSessionManager`;
   - note di affidabilita nel `SeniorDataAnalystEngine`;
   - `AgentContext` aggiornato con `learning_state` e `learning_events`;
   - 10 test dedicati.
10. **Milestone intermedia - Analytical Reasoning Layer**, completata in questa
    iterazione:
   - classe `AnalyticalReasoningLayer`;
   - strategia analitica locale JSON-serializzabile;
   - ranking delle analisi tramite intent, pattern e `learning_state`;
   - esclusione esplicita di analisi incompatibili con lo schema;
   - domande di chiarimento per richieste ambigue, metriche e soglie SLA;
   - integrazione con `DataProcessorAgent`, `AnalysisSessionManager`,
     `SeniorDataAnalystEngine` e `AgentContext`;
   - 9 test dedicati.
11. **Milestone 7 - Advanced Statistical Engine**, completata in questa
    iterazione:
   - classe `AdvancedStatisticalEngine`;
   - statistiche descrittive, percentili e dispersione robusta;
   - outlier detection IQR, z-score e modified z-score;
   - trend rolling, growth percent e month-over-month;
   - confronto soglie/SLA;
   - matrici Pearson, Spearman e Kendall;
   - frequency table e missing/completeness analysis;
   - integrazione con `DataProcessorAgent`, `AnalyticalReasoningLayer`,
     `PatternKnowledgeEngine`, `SeniorDataAnalystEngine` e `AgentContext`;
   - 11 test dedicati.
12. **Milestone 8 - Anomaly Detection Engine**, completata in questa
    iterazione:
   - classe `AnomalyDetectionEngine`;
   - rilevazione outlier numerici;
   - spike temporali e cambi improvvisi;
   - degrado prestazionale;
   - drift rispetto a baseline;
   - violazioni soglia/SLA;
   - severity e `confidence_score` per ogni anomalia;
   - integrazione con `DataProcessorAgent`, `AnalyticalReasoningLayer`,
     `AnalysisSessionManager`, `SeniorDataAnalystEngine` e `AgentContext`;
   - 11 test dedicati.
13. **Milestone 9 - Domain Intelligence Packs Architecture**, completata in
    questa iterazione:
   - directory `domain_packs/` con pack iniziale `telepedaggio`;
   - classe `DomainPackLoader`;
   - discovery, validazione, caricamento ed export JSON-safe dei pack;
   - suggerimento pack tramite richiesta utente e metadata dataframe;
   - funzionamento completamente locale senza OpenAI;
   - integrazione con `PatternKnowledgeEngine`, `AnalyticalReasoningLayer`,
     `SeniorDataAnalystEngine`, `DataProcessorAgent` e `AgentContext`;
   - sezione report "Dominio riconosciuto";
   - 8 test dedicati.
14. **Milestone 11 - Root Cause Analysis Engine**, completata in questa
    iterazione:
   - classe `RootCauseAnalysisEngine`;
   - raggruppamento locale di anomalie per colonna, periodo, tipo, severita e
     segnali di trend/degrado;
   - inferenza di possibili cause radice solo da evidenze presenti nel payload;
   - separazione esplicita tra evidence, hypothesis e recommendation;
   - severity e `confidence_score` per ogni causa proposta;
   - output JSON-serializzabile e stato `insufficient_evidence` quando le prove
     non bastano;
   - integrazione con `DataProcessorAgent`, `AnalyticalReasoningLayer`,
     `AnalysisSessionManager`, `SeniorDataAnalystEngine`, `ExplainabilityEngine`
     e `AgentContext`;
   - sezione report "Possibili cause radice";
   - 9 test dedicati.

### Moduli implementati

#### Entry point e orchestrazione

- `main.py`: avvio dell'applicazione.
- `app_dash.py`: bootstrap Dash e wrapper di compatibilita.
- `coordinator.py`: pipeline sequenziale Hub & Spoke.

#### UI

- `ui/layout.py`: layout, componenti e stile della dashboard.
- `ui/callbacks.py`: callback per upload, Oracle, pipeline, timeline, risultati,
  feedback, PDF e chat follow-up.

#### Service layer

- `services/analysis_service.py`: parsing upload, stato runtime, esecuzione
  pipeline e follow-up deterministici.
- `services/oracle_service.py`: verifica connessione Oracle.
- `services/analysis_engine.py`: piani ed esecuzioni deterministiche Pandas.
- `services/semantic_memory.py`: embeddings, cosine similarity e fallback
  testuale.
- `services/autonomous_analyst.py`: planner ed executor multi-step
  deterministico.
- `services/senior_data_analyst_engine.py`: relazione professionale locale
  derivata esclusivamente dai risultati deterministici, presente su `main`.
- `services/analysis_session_manager.py`: sessioni e iterazioni analitiche in
  memoria, presente su `main`.
- `services/pattern_knowledge_engine.py`: Knowledge Base locale dei pattern
  analitici, presente nel commit locale `4f3ad13`.
- `services/learning_engine.py`: apprendimento locale da utilizzi, feedback,
  confidence e audit trail, presente su
  `feature/milestone-6-learning-engine`.
- `services/analytical_reasoning_layer.py`: strategy builder locale per
  decidere ordine, esclusioni, chiarimenti e reasoning trace delle analisi.
- `services/advanced_statistical_engine.py`: libreria statistica locale per
  percentili, dispersione, outlier, trend, soglie, correlazioni e completezza.
- `services/anomaly_detection_engine.py`: motore locale per anomalie, spike,
  degrado, drift, SLA, severity e raccomandazioni spiegabili.
- `services/domain_pack_loader.py`: loader locale per domain pack, discovery,
  validazione, suggerimento pack ed export JSON-safe.
- `services/root_cause_analysis_engine.py`: motore locale per raggruppare
  anomalie, pattern e statistiche in possibili cause radice spiegabili.
- `services/explainability_engine.py`: motore locale per spiegazioni
  strutturate, evidence e reasoning path JSON-safe.

#### Persistenza e utility

- `utils/context.py`: `AgentContext` condiviso.
- `utils/data_analysis.py`: profiling deterministico del dataframe.
- `utils/query_history_manager.py`: memoria SQLite delle query.
- `utils/analysis_history_manager.py`: memoria SQLite dei pattern analitici,
  feedback, confidence ed embedding.
- `utils/conversation_manager.py`: storico e serializzazione delle
  conversazioni.
- `utils/chart_generator.py`: grafici Plotly automatici e richiesti.
- `utils/pdf_generator.py`: export PDF.
- `utils/oracle_query_validator.py`: enforcement read-only.
- `utils/learning_monitor.py`: statistiche sulla memoria query.
- `utils/logging_config.py`: logging applicativo con rotazione.

#### Connettori

- `connectors/data_connectors.py`: connettori CSV, Excel e Oracle.

### Agenti presenti

La pipeline principale contiene sette agenti:

1. `DataSourceManagerAgent`: acquisisce CSV, Excel o dati Oracle.
2. `QuerySuggestionAgent`: interpreta la richiesta e propone query o colonne,
   riusando lo storico quando possibile.
3. `DataExtractorAgent`: prepara il piano di estrazione.
4. `DataValidatorAgent`: valida la disponibilita e la qualita dei dati.
5. `DataProcessorAgent`: produce profiling, piani e risultati deterministici.
6. `AnalystAgent`: usa `SeniorDataAnalystEngine` come motore primario locale e
   conserva l'eventuale output OpenAI come arricchimento opzionale.
7. `ReportGeneratorAgent`: usa il report locale come fonte primaria e puo
   aggiungere un arricchimento testuale OpenAI non bloccante.

E inoltre presente `ConversationAgent`, usato dalla chat post-analisi per le
richieste che non vengono risolte dai follow-up deterministici.

### Motori deterministici disponibili

- Profiling del dataframe:
  - righe, colonne e tipi;
  - null;
  - duplicati;
  - statistiche numeriche;
  - distribuzioni categoriali;
  - correlazioni;
  - range temporali.
- `AnalysisEngine`:
  - conteggio occorrenze;
  - top N;
  - somma, media, minimo, massimo e conteggio;
  - trend temporali;
  - null detection;
  - duplicate detection.
- `AutonomousAnalyst`:
  - pianificazione multi-step euristica;
  - distribuzioni;
  - trend;
  - durate tra date;
  - aggregazioni numeriche;
  - controlli di qualita.
- Follow-up locali:
  - conteggio ticket per stato;
  - grafici richiesti;
  - andamento chiusure;
  - tempo medio tra creazione e risoluzione.
- `SeniorDataAnalystEngine`, presente su `main`:
  - executive summary;
  - KPI;
  - trend analysis;
  - anomaly analysis descrittiva;
  - segmentation analysis;
  - data quality;
  - raccomandazioni;
  - report Markdown.

### Memoria e apprendimento disponibili

- `data/query_history.db`: query, descrizione, feedback e contatori.
- `data/analysis_history.db`: piani analitici, colonne, feedback, confidence,
  utilizzi, successi ed embedding.
- `LearningEngine`: stato in memoria con eventi di utilizzo, feedback,
  promozioni, declassamenti, raccomandazioni e struttura pronta per SQLite.
- Riuso di pattern con feedback positivo.
- Similarita semantica tramite embedding OpenAI quando disponibile.
- Fallback locale tramite `SequenceMatcher`.
- Aggiornamento di query e pattern dai pulsanti “Utile” e “Non utile”.

Il Learning Engine e oggi un motore locale in memoria: apprende e produce audit
trail durante il processo Python, ma la persistenza SQLite dedicata e ancora un
passo successivo.

### Fallback locali implementati

- Analysis Engine completamente locale.
- Autonomous Analyst completamente locale.
- Grafici Plotly completamente locali.
- Query e pattern history su SQLite locale.
- Similarita testuale locale quando embeddings non sono disponibili.
- Follow-up riconoscibili calcolati localmente.
- Senior Data Analyst Engine e report finale completamente locali.
- `BaseAgent` puo essere istanziato senza `OPENAI_API_KEY`.
- `AnalystAgent` completa l'analisi locale senza OpenAI.
- `ReportGeneratorAgent` produce il report finale anche senza
  `OPENAI_API_KEY`.
- Analysis Session Manager completamente locale e senza chiamate OpenAI.
- Pattern Knowledge Engine completamente locale e senza chiamate OpenAI.
- Learning Engine completamente locale e senza chiamate OpenAI.
- Analytical Reasoning Layer completamente locale e senza chiamate OpenAI.
- Advanced Statistical Engine completamente locale e senza chiamate OpenAI.
- Anomaly Detection Engine completamente locale e senza chiamate OpenAI.
- Domain Pack Loader completamente locale e senza chiamate OpenAI.
- Root Cause Analysis Engine completamente locale e senza chiamate OpenAI.
- Explainability Engine completamente locale e senza chiamate OpenAI.

### Qualita verificata

- Suite pytest: **137 test superati**.
- Test dedicati al Senior Data Analyst Engine: **7 superati**.
- Test dedicati all'Analysis Session Manager: **8 superati**.
- Test dedicati al Pattern Knowledge Engine: **9 superati**.
- Test dedicati al Learning Engine: **10 superati**.
- Test dedicati all'Analytical Reasoning Layer: **9 superati**.
- Test dedicati all'Advanced Statistical Engine: **11 superati**.
- Test dedicati all'Anomaly Detection Engine: **11 superati**.
- Test dedicati al Domain Pack Loader: **8 superati**.
- Test dedicati al Root Cause Analysis Engine: **9 superati**.
- Copertura presente per Analysis Engine, history, feedback, semantic memory,
  autonomous analysis, follow-up, grafici richiesti, sicurezza Oracle e report
  locale.
- Restano scoperti test end-to-end della dashboard e molte callback Dash.

## Architettura corrente

```text
Input
  - richiesta in linguaggio naturale
  - CSV / Excel / Oracle read-only
        |
        v
Analysis Session Manager
  - sessione e iterazioni
  - classificazione locale richiesta
  - contesto per follow-up
        |
        v
Pattern Knowledge Engine
  - pattern analitici
  - best practice
  - step raccomandati
        |
        v
Domain Pack Loader
  - domain pack locali
  - KPI, regole, domande e terminologia
  - nessuna dipendenza da OpenAI
        |
        v
Learning Engine
  - eventi utilizzo e feedback
  - confidence score
  - promozione e declassamento pattern
  - raccomandazioni di miglioramento
        |
        v
Analytical Reasoning Layer
  - strategia ordinata
  - razionale delle analisi
  - esclusioni motivate
  - domande di chiarimento
        |
        v
Advanced Statistical Engine
  - percentili e dispersione
  - outlier e soglie
  - trend rolling
  - correlazioni e completezza
        |
        v
Anomaly Detection Engine
  - outlier e spike
  - degrado e drift
  - violazioni SLA
  - severity e confidence
        |
        v
Root Cause Analysis Engine
  - gruppi di anomalie correlate
  - cause possibili supportate da evidenze
  - alternative e raccomandazioni
        |
        v
Analysis Engine
  - profiling Pandas
  - AnalysisPlan singolo
  - oppure AutonomousAnalysisPlan multi-step
  - memoria query e pattern
  - risultati JSON-serializzabili
        |
        v
Senior Data Analyst Engine
  - KPI
  - evidenze
  - trend
  - segmentazioni
  - anomalie descrittive
  - qualita dati
  - raccomandazioni
        |
        v
Report
  - Markdown locale
  - grafici Plotly
  - PDF
  - eventuale arricchimento OpenAI
        |
        v
Chat follow-up e feedback
```

### Flusso dati

`AgentContext` e l'oggetto condiviso tra gli agenti. Contiene:

- input e metadata;
- dataframe in `raw_data`;
- risultati di validazione;
- `processed_data`;
- piano e risultati deterministici;
- pattern analitici rilevati e step suggeriti;
- learning state ed eventi di apprendimento;
- strategia analitica adottata e reasoning trace;
- risultati statistici avanzati;
- risultati anomaly detection;
- risultati root cause analysis;
- domain pack context;
- metadati di memoria e confidence;
- risultati autonomous;
- insight;
- report finale;
- errori.

La dashboard mantiene inoltre uno stato runtime in memoria nel processo Python.
Le elaborazioni vengono avviate in un thread e la UI interroga periodicamente
lo stato per aggiornare timeline e risultati.

## Stato dell'autonomia

| Ambito | Stato | Note |
| --- | --- | --- |
| Analysis Engine | Completamente locale | Calcoli Python/Pandas verificabili. |
| Analysis Session Manager | Completamente locale | Sessioni iterative in memoria, nessuna chiamata esterna. |
| Pattern Knowledge Engine | Completamente locale | Riconoscimento pattern e suggerimenti deterministici. |
| Learning Engine | Completamente locale | Confidence, promozione, declassamento e audit trail in memoria. |
| Analytical Reasoning Layer | Completamente locale | Strategia analitica, esclusioni e chiarimenti senza OpenAI. |
| Advanced Statistical Engine | Completamente locale | Percentili, dispersione, outlier, trend, soglie, correlazioni e completezza. |
| Anomaly Detection Engine | Completamente locale | Outlier, spike, degrado, drift, SLA, severity e raccomandazioni. |
| Domain Pack Loader | Completamente locale | Conoscenza di dominio caricabile senza modificare il core engine. |
| Root Cause Analysis Engine | Completamente locale | Cause radice possibili derivate solo da evidenze disponibili. |
| Explainability Engine | Completamente locale | Reasoning path, evidence, confidence e algoritmi usati in JSON-safe. |
| Senior Data Analyst Engine | Completamente locale | Insight, KPI, note metodologiche e raccomandazioni locali. |
| Report locale | Completamente locale | Il report finale puo essere prodotto senza `OPENAI_API_KEY`. |
| Interpretazione linguistica | OpenAI opzionale/parzialmente necessaria | Alcuni agenti precedenti usano ancora OpenAI quando non esiste un fallback locale. |
| Miglioramento stilistico | OpenAI opzionale | Analyst e Report Generator usano OpenAI solo come arricchimento non bloccante. |

## Dipendenza attuale da OpenAI

### Componenti che utilizzano ancora OpenAI

- `QuerySuggestionAgent`:
  - usa OpenAI quando non trova una query storica riutilizzabile;
  - e particolarmente rilevante per la generazione SQL Oracle.
- `DataExtractorAgent`:
  - genera il piano testuale di estrazione tramite OpenAI.
- `DataValidatorAgent`:
  - genera il report di validazione tramite OpenAI;
  - la validazione attuale non e ancora un motore locale completo.
- `DataProcessorAgent`:
  - calcola risultati deterministici localmente;
  - usa ancora OpenAI per il report testuale di processing;
  - senza fallback dedicato, questo passaggio puo ancora interrompere la
    pipeline completa se la chiave manca.
- `ConversationAgent`:
  - usa OpenAI per domande follow-up non riconosciute dai percorsi locali.
- `SemanticMemory`:
  - usa embeddings OpenAI quando configurati;
  - dispone gia di fallback locale testuale.
- `AnalystAgent` e `ReportGeneratorAgent`:
  - usano il Senior Data Analyst Engine e il report locale come fonti primarie;
  - OpenAI e solo un arricchimento testuale opzionale;
  - il report finale viene prodotto anche senza `OPENAI_API_KEY`.

### Componenti completamente locali

- lettura CSV ed Excel;
- connessione ed esecuzione Oracle read-only dopo che la query e disponibile;
- query safety;
- profiling Pandas;
- `AnalysisEngine`;
- `AutonomousAnalyst`;
- `AnalysisSessionManager`;
- `PatternKnowledgeEngine`;
- `LearningEngine`;
- `AnalyticalReasoningLayer`;
- `AdvancedStatisticalEngine`;
- `AnomalyDetectionEngine`;
- `DomainPackLoader`;
- `RootCauseAnalysisEngine`;
- `ExplainabilityEngine`;
- `SeniorDataAnalystEngine`;
- grafici Plotly;
- PDF;
- history SQLite;
- feedback e confidence;
- follow-up deterministici gia riconosciuti;
- report finale locale prodotto dal `SeniorDataAnalystEngine`;
- sessioni analitiche in memoria tramite `AnalysisSessionManager`.

### Obiettivi di eliminazione futura

1. Rendere `DataProcessorAgent` non bloccante senza OpenAI.
2. Sostituire la validazione LLM con un Data Quality Engine locale.
3. Sostituire il piano di estrazione LLM con schema discovery e rule engine.
4. Implementare text-to-SQL locale e validato per Oracle.
5. Rendere la chat follow-up capace di pianificare analisi locali generiche.
6. Sostituire gli embeddings remoti con embedding locali opzionali.
7. Mantenere OpenAI solo come provider intercambiabile e disattivabile.
8. Raggiungere una pipeline completa funzionante con
   `OPENAI_API_KEY` assente.

## Roadmap

### ✅ Milestone 4 - Analysis Session Manager

**Stato:** Completata.

**Obiettivo raggiunto:** introdurre sessioni iterative locali, classificazione
delle richieste, contesto per follow-up ed export sintetico.

**Moduli:** `services/analysis_session_manager.py`,
`tests/test_analysis_session_manager.py`.

**Passo futuro non bloccante:** persistenza SQLite e integrazione completa con
dashboard e conversation manager.

### ✅ Milestone 5 - Pattern Knowledge Engine

**Stato:** Completata.

**Obiettivo raggiunto:** riconoscere pattern analitici, suggerire
automaticamente analisi e arricchire piano e report con best practice.

**Moduli:** `services/pattern_knowledge_engine.py`,
`agents/data_processor.py`, `services/analysis_session_manager.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** persistenza SQLite e creazione dinamica di
pattern tramite Learning Engine.

### ✅ Milestone 6 - Learning Engine

**Stato:** Completata.

**Obiettivo raggiunto:** permettere al sistema di imparare localmente dalle
analisi effettuate e dal feedback utente.

Il motore:

- aggiornare i confidence score;
- promuovere pattern efficaci;
- declassare pattern inutili;
- costruire esperienza analitica riusabile;
- mantenere audit trail delle decisioni di apprendimento.

**Moduli:** `services/learning_engine.py`,
`services/pattern_knowledge_engine.py`, `services/analysis_session_manager.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** persistenza SQLite dedicata, collegamento
completo con feedback dashboard e creazione dinamica di nuovi pattern.

**Dipendenza:** Milestone 4 e 5.

### ✅ Milestone intermedia - Analytical Reasoning Layer

**Stato:** Completata.

**Obiettivo raggiunto:** introdurre un layer locale che decide quali analisi
eseguire, in quale ordine, quali evitare e quando chiedere chiarimenti.

Il motore:

- legge richiesta utente, metadata dataframe, pattern rilevati e stato di
  apprendimento;
- costruisce `recommended_sequence` con priorita, rationale, colonne richieste,
  dipendenze, output atteso e confidence;
- produce `excluded_analyses` quando mancano colonne data, numeriche o
  categoriali;
- produce `clarification_questions` per richieste ambigue, metriche multiple o
  soglie SLA non dichiarate;
- esporta `reasoning_trace` JSON-serializzabile.

**Moduli:** `services/analytical_reasoning_layer.py`,
`agents/data_processor.py`, `services/analysis_session_manager.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** collegare la strategy all'orchestrazione
multi-step effettiva, trasformando gli step raccomandati in esecuzioni Pandas
quando il motore statistico supporta tutte le analisi richieste.

**Dipendenza:** Milestone 5 e 6.

### ✅ Milestone 7 - Advanced Statistical Engine

**Stato:** Completata.

**Obiettivo raggiunto:** ampliare le analisi locali con metodi statistici
robusti e JSON-serializzabili senza chiamate OpenAI.

Il motore supporta:

- statistiche descrittive;
- percentili P10, P25, P50, P75, P90, P95, P99;
- dispersione con range, IQR, varianza, deviazione standard, coefficiente di
  variazione e MAD;
- outlier detection con IQR, z-score e modified z-score;
- trend con rolling mean, rolling standard deviation, growth percent e
  month-over-month;
- confronto soglie/SLA;
- matrici di correlazione Pearson, Spearman e Kendall;
- frequency table;
- missing/completeness analysis.

**Moduli:** `services/advanced_statistical_engine.py`,
`agents/data_processor.py`, `services/analytical_reasoning_layer.py`,
`services/pattern_knowledge_engine.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** aggiungere regressione, trend decomposition e
orchestrazione automatica degli step statistici come esecuzioni distinte.

**Dipendenza:** Analysis Engine e Pattern Knowledge Engine.

### ✅ Milestone 8 - Anomaly Detection Engine

**Stato:** Completata.

**Obiettivo raggiunto:** riconoscimento automatico e spiegabile di anomalie
statistiche e segnali di degrado senza chiamate OpenAI.

Il motore supporta:

- outlier numerici;
- spike temporali;
- degrado prestazionale;
- drift rispetto a baseline;
- cambi improvvisi;
- violazioni soglia/SLA;
- severity, confidence score, evidenza e raccomandazione per ogni anomalia.

**Moduli:** `services/anomaly_detection_engine.py`,
`agents/data_processor.py`, `services/analytical_reasoning_layer.py`,
`services/analysis_session_manager.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** aggiungere stagionalita, change point detection
piu robusta e visualizzazioni dedicate per anomalie e SLA.

**Dipendenza:** Milestone 7.

### ✅ Milestone 9 - Domain Intelligence Packs Architecture

**Stato:** Completata.

**Obiettivo raggiunto:** caricare conoscenza di dominio locale senza modificare
il core engine e senza chiamate OpenAI.

Il loader supporta:

- discovery dei pack disponibili in `domain_packs/`;
- validazione dei file obbligatori;
- caricamento del pack e export JSON-safe;
- suggerimento pack da richiesta utente e metadata dataframe;
- fallback non bloccante quando nessun pack viene riconosciuto.

Il pack iniziale `telepedaggio` include concetti, pattern, KPI, regole
strategiche, domande di chiarimento, terminologia e template report per
contratti, sottoscrizioni, attivazioni, device/OBU, antenne e consegne.

**Moduli:** `services/domain_pack_loader.py`, `domain_packs/`,
`agents/data_processor.py`, `services/pattern_knowledge_engine.py`,
`services/analytical_reasoning_layer.py`,
`services/senior_data_analyst_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** persistenza/versioning dei pack, UI di gestione
pack e ulteriori domini verticali.

**Dipendenza:** Milestone 5, 7 e 8.

### ✅ Milestone 11 - Root Cause Analysis Engine

**Stato:** Completata.

**Obiettivo raggiunto:** proporre possibili cause radice spiegabili a partire
da anomalie, pattern, statistiche, strategia analitica e contesto di dominio
gia presenti nel payload, senza chiamate OpenAI.

Il motore:

- legge `anomaly_detection_results`, `advanced_statistical_results`,
  `analytical_strategy`, pattern rilevati e `domain_pack_context`;
- raggruppa anomalie per stessa colonna, periodo, tipo, severita e segnali di
  trend/degrado;
- produce cause possibili con severity, confidence score, metriche impattate,
  anomalie correlate, evidenze, spiegazioni alternative, azioni consigliate e
  reasoning trace;
- restituisce `insufficient_evidence` quando non ci sono prove sufficienti;
- usa il domain pack solo come guida terminologica e strategica, mai come
  prova causale.

**Moduli:** `services/root_cause_analysis_engine.py`,
`agents/data_processor.py`, `services/analytical_reasoning_layer.py`,
`services/analysis_session_manager.py`,
`services/senior_data_analyst_engine.py`,
`services/explainability_engine.py`, `utils/context.py`.

**Passo futuro non bloccante:** collegare le cause radice a visualizzazioni,
drill-down per segmento e validazione human-in-the-loop.

**Dipendenza:** Milestone 7, 8 e 9.

### Milestone 12 - Predictive Analytics Engine

**Obiettivo:** introdurre:

- forecasting;
- previsione KPI;
- simulazioni;
- scenari.

Ogni previsione dovra includere metodo, perimetro, metriche di errore,
intervallo di confidenza e limiti d'uso.

**Moduli previsti:** `services/predictive_analytics_engine.py`, model registry,
feature engineering, session manager e report.

**Priorita:** Media.

**Dipendenza:** Milestone 7, 8 e 9.

### Milestone 13 - Natural Language Planner

**Obiettivo:** trasformare automaticamente una richiesta utente in un piano
analitico completo.

Il planner dovra identificare obiettivo, metriche, filtri, periodo,
segmentazioni, soglie, controlli di qualita, step, dipendenze e output attesi.

**Moduli previsti:** `services/natural_language_planner.py`, Pattern Knowledge
Engine, Session Manager, schema discovery e motore locale di intent.

**Priorita:** Critica per l'autonomia.

**Dipendenza:** Milestone 5, 6, 7 e 9.

### Milestone 14 - Knowledge Consolidation Engine

**Obiettivo:** fondere pattern simili e costruire una conoscenza strutturata,
versionata e non ridondante.

Il motore dovra:

- riconoscere pattern equivalenti;
- unire evidenze e best practice;
- separare conoscenza generale e specifica del dominio;
- gestire versioni, conflitti e obsolescenza;
- produrre una Knowledge Base persistente.

**Moduli previsti:** `services/knowledge_consolidation_engine.py`, Learning
Engine, Pattern Knowledge Engine e storage SQLite.

**Priorita:** Alta.

**Dipendenza:** Milestone 6.

### Milestone 15 - Autonomia completa

**Obiettivo:** rendere OpenAI opzionale e permettere al sistema di lavorare
completamente offline.

Sono necessari:

- interpretazione locale della richiesta;
- planner locale;
- embedding locali;
- text-to-SQL locale e read-only;
- validazione e data quality locali;
- follow-up locali generalizzati;
- motori statistici, anomaly e predictive;
- report locale completo;
- provider abstraction per eventuali arricchimenti esterni.

**Priorita:** Strategica.

**Dipendenza:** Tutte le milestone precedenti.

## Debito tecnico

- Il branch corrente e `feature/milestone-11-root-cause-analysis`, derivato da
  `origin/main`, con modifiche locali non committate per la Milestone 11.
- `DataProcessorAgent` chiama ancora OpenAI in modo bloccante dopo avere
  calcolato i risultati deterministici.
- `DataExtractorAgent` e `DataValidatorAgent` non hanno fallback locali
  completi.
- `ConversationAgent` dipende da OpenAI per le richieste non coperte dalle
  euristiche di follow-up.
- `QuerySuggestionAgent` dipende da OpenAI quando la history non contiene un
  match; manca un text-to-SQL locale generale.
- Il semantic matching locale usa `SequenceMatcher`, che misura somiglianza
  testuale e non semantica.
- Il modello chat e hardcoded a `gpt-3.5-turbo`; manca una configurazione
  provider/model centralizzata.
- Le history query e analysis sono database separati e non modellano una
  sessione completa.
- `AnalysisSessionManager` usa storage in memoria e non e ancora collegato alla
  dashboard, al coordinator o a SQLite.
- `PatternKnowledgeEngine` resta basato su un catalogo statico; il
  `LearningEngine` ne modifica ranking e affidabilita, ma non crea ancora nuovi
  pattern persistenti.
- `LearningEngine` usa storage in memoria e non persiste ancora eventi e
  confidence su SQLite.
- Gli step suggeriti dalla Knowledge Base non vengono ancora orchestrati
  automaticamente: arricchiscono piano e report, ma non sostituiscono i
  risultati deterministici realmente eseguiti.
- Lo stato Dash e globale/in-memory e non supporta correttamente multiutente,
  multiprocesso o deployment distribuito.
- Le elaborazioni usano thread daemon senza job queue, cancellazione, timeout,
  retry o persistenza dello stato.
- La pipeline principale e sequenziale; il lavoro parallelo degli agenti non e
  ancora implementato.
- La UI mostra una timeline, ma non un vero grafo di esecuzione con dipendenze,
  eventi e frecce persistenti.
- Il sistema non esegue discovery completo dello schema Oracle, foreign key,
  relazioni o semantic layer.
- L'input Oracle richiede ancora una query esplicita nel flusso principale.
- Le credenziali Oracle sono mantenute in memoria di processo; manca un secret
  manager per deployment.
- La gestione automatica delle dipendenze/librerie richiesta nella visione
  iniziale non e implementata e deve essere progettata con sandbox e allowlist.
- Il PDF deve essere verificato visivamente con report Markdown complessi.
- La documentazione storica (`APPLICATION_CONTEXT.md`, `CAPABILITIES.md` e
  alcune sezioni README) contiene descrizioni precedenti alla modalita locale e
  necessita allineamento.
- La struttura README dei file non elenca ancora tutti i moduli recenti.
- I test non coprono end-to-end UI, callback Dash, concorrenza, Oracle reale,
  PDF visuale e assenza della chiave OpenAI sull'intera pipeline.
- Mancano type checking, linting e quality gate multipiattaforma uniforme; gli
  script principali sono orientati a PowerShell.
- La rilevazione anomalie del Senior Data Analyst Engine e descrittiva e basata
  su statistiche aggregate, non su un algoritmo robusto row-level.
- Non esiste un contratto/versione formale per `processed_data`, `insights` e i
  payload salvati nelle history.
- I log e i database locali non hanno retention, cifratura o gestione esplicita
  dei dati sensibili.
- Le eccezioni in alcuni manager vengono ignorate intenzionalmente con
  fallback; serve telemetria piu precisa per distinguere degradazione e
  successo.

## Idee future

Le idee emerse durante lo sviluppo, incluse quelle non ancora implementate,
sono:

- UX visuale stile n8n con canvas, nodi, porte, frecce e animazioni dello stato
  degli agenti.
- Esecuzione parallela degli agenti quando non esistono dipendenze tra step.
- Visualizzazione di input, output, durata, errori e retry per ogni nodo.
- Sessioni persistenti riapribili con cronologia completa.
- Conversazione post-analisi realmente libera, capace di generare nuovi piani
  sullo stesso file, su un nuovo file o su una query.
- Versionamento delle analisi successive e confronto tra risultati.
- Next best action suggerite automaticamente.
- Discovery automatico di schema Oracle, tabelle, colonne, primary key,
  foreign key e relazioni.
- Grafo semantico del database per richieste in linguaggio naturale.
- Generazione, validazione, spiegazione ed esecuzione read-only di SQL da
  linguaggio naturale.
- Anteprima della query generata e conferma opzionale prima dell'esecuzione.
- Supporto futuro ad altri database tramite adapter.
- Catalogo dati con descrizioni business delle colonne.
- Data quality score locale e regole per dominio.
- KPI library configurabile per settore.
- Dashboard di apprendimento con pattern migliori, peggiori e drift.
- Feedback granulare con rating, motivazione e correzione proposta.
- Memoria per cliente, workspace e dominio con isolamento dei dati.
- Embedding locali per privacy e funzionamento offline.
- Modelli linguistici locali opzionali dietro una provider abstraction.
- Motore di chiarimento che identifichi automaticamente ambiguita, metriche,
  filtri, periodo, granularita e output desiderato.
- Planner capace di stimare costo, tempo e rischio di ogni analisi.
- Auto-installazione controllata di librerie tramite allowlist, ambiente
  isolato, scansione e approvazione; mai installazione arbitraria.
- Forecast, scenario analysis, what-if e simulazioni.
- Rilevazione drift di schema, dati, KPI e performance.
- Alert e automazioni pianificate su fonti dati.
- Export DOCX, presentazioni e pacchetti executive oltre a PDF.
- Audit trail completo: dato sorgente, query, piano, versione motore, regole,
  risultato e feedback.
- Benchmark automatici per confrontare piani, prompt e motori.
- Human-in-the-loop configurabile per operazioni ad alto rischio.
- Plugin/skill marketplace interno con permessi espliciti.

## Ultimo aggiornamento

- **Data:** 26 giugno 2026
- **Branch Git:** `feature/milestone-11-root-cause-analysis`
- **HEAD locale:** `cf13255 Revise README for Skills Agent overview and details`
- **HEAD remoto `origin/main`:** `cf13255 Revise README for Skills Agent overview and details`
- **Stato repository:** modifiche locali non committate per la Milestone 11.
- **Azione Git pendente:** review delle modifiche, commit e pubblicazione della
  branch.
- **Modifiche locali principali:** `RootCauseAnalysisEngine`, integrazione con
  Data Processor, Analytical Reasoning Layer, Analysis Session Manager, Senior
  Data Analyst Engine, Explainability Engine, context, README e stato progetto.
- **Numero test:** 137 superati.
- **Quality gate:** `python3 -m pytest` superato; `python3 -m compileall agents connectors services ui utils main.py app_dash.py coordinator.py`
  da rieseguire dopo ogni modifica; `git diff --check` da rieseguire dopo ogni
  modifica.
