# Project Status

## Visione del progetto

`skills_agent` non e un semplice tool di analisi dati. La visione finale e
costruire un sistema agentico autonomo che trasformi una richiesta di business
in un processo analitico verificabile, conversazionale e progressivamente
migliore.

Il sistema deve essere capace di:

- acquisire dati da CSV, Excel e Oracle;
- comprendere richieste espresse in linguaggio naturale;
- porre domande di chiarimento quando obiettivi, vincoli o dati sono ambigui;
- costruire ed eseguire analisi statistiche reali sui dati disponibili;
- distinguere sempre interpretazione linguistica e calcolo numerico;
- dialogare con l'utente attraverso iterazioni e analisi successive;
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

## Stato attuale

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

Nel worktree corrente e stata implementata la Milestone 4 - Analysis Session
Manager, ancora da committare:

- sessioni in memoria con struttura versionata;
- iterazioni append-only;
- classificazione locale delle richieste;
- contesto per follow-up;
- export sintetico JSON-serializzabile;
- struttura predisposta per una futura persistenza SQLite.

Nota sulla numerazione: le milestone storiche nel README usano i numeri 2, 2.5,
3 e 4. La roadmap evolutiva richiesta piu avanti in questo documento riparte da
“Milestone 4 - Analysis Session Manager”. La numerazione deve essere
normalizzata in una futura revisione documentale.

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
  memoria, implementato nel worktree corrente.

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
- Riuso di pattern con feedback positivo.
- Similarita semantica tramite embedding OpenAI quando disponibile.
- Fallback locale tramite `SequenceMatcher`.
- Aggiornamento di query e pattern dai pulsanti “Utile” e “Non utile”.

Questo e oggi un meccanismo di memoria e ranking, non ancora un Learning Engine
autonomo completo.

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

### Qualita verificata

- Suite pytest: **70 test superati**.
- Test dedicati al Senior Data Analyst Engine: **7 superati**.
- Test dedicati all'Analysis Session Manager: **8 superati**.
- Copertura presente per Analysis Engine, history, feedback, semantic memory,
  autonomous analysis, follow-up, grafici richiesti, sicurezza Oracle e report
  locale.
- Restano scoperti test end-to-end della dashboard e molte callback Dash.

## Architettura corrente

```text
Input utente
  - richiesta in linguaggio naturale
  - CSV / Excel
  - Oracle read-only
        |
        v
Pipeline agentica
  DataSourceManager
        -> QuerySuggestion
        -> DataExtractor
        -> DataValidator
        -> DataProcessor
        -> Analyst
        -> ReportGenerator
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
Report finale
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
- metadati di memoria e confidence;
- risultati autonomous;
- insight;
- report finale;
- errori.

La dashboard mantiene inoltre uno stato runtime in memoria nel processo Python.
Le elaborazioni vengono avviate in un thread e la UI interroga periodicamente
lo stato per aggiornare timeline e risultati.

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

La roadmap seguente usa la numerazione richiesta per il prossimo ciclo di
sviluppo. Non coincide con la numerazione storica dei commit gia integrati.

### Milestone 4 - Analysis Session Manager

**Obiettivo**

Gestione strutturata delle sessioni analitiche: input, sorgente, metadata del
dataframe, richieste successive, piani, risultati, insight e snapshot dei
report.

**Motivazione**

Una sessione esplicita e necessaria per riprendere analisi, confrontare
iterazioni e costruire apprendimento affidabile. La prima implementazione usa
storage Python in memoria e prepara il contratto dati per SQLite.

**Moduli coinvolti**

- `services/analysis_session_manager.py`;
- `tests/test_analysis_session_manager.py`;
- futura integrazione con `utils/conversation_manager.py`;
- futura integrazione con `services/analysis_service.py` e `ui/callbacks.py`;
- futuro repository SQLite.

**Priorita:** Critica. Base in-memory implementata; integrazione UI e
persistenza ancora da completare.

**Dipendenza:** Base per Knowledge Base, Learning Engine e autonomia completa.

### Milestone 5 - Knowledge Base dei pattern analitici

**Obiettivo**

Unificare query, piani, metriche, schema, risultati, feedback e contesto di
business in una knowledge base interrogabile.

**Motivazione**

Le due history SQLite sono separate e memorizzano pattern limitati. Serve una
memoria strutturata e versionata che sappia distinguere sorgente, dominio,
schema e validita temporale.

**Moduli coinvolti**

- `utils/query_history_manager.py`;
- `utils/analysis_history_manager.py`;
- `services/semantic_memory.py`;
- nuovo `services/knowledge_base.py`;
- migrazioni SQLite.

**Priorita:** Alta.

**Dipendenza:** Analysis Session Manager.

### Milestone 6 - Learning Engine

**Obiettivo**

Trasformare feedback, esiti, correzioni e riutilizzi in aggiornamenti operativi
di ranking, confidence, scelta del piano e next best action.

**Motivazione**

Il sistema oggi memorizza e riusa, ma non apprende strategie complesse ne
misura in modo completo la qualita dell'output.

**Moduli coinvolti**

- nuovo `services/learning_engine.py`;
- Knowledge Base;
- `utils/learning_monitor.py`;
- callback feedback;
- metriche di successo e audit.

**Priorita:** Alta.

**Dipendenza:** Milestone 4 e 5.

### Milestone 7 - Rule Engine

**Obiettivo**

Implementare regole dichiarative per chiarimenti, selezione analisi,
validazione, scelta colonne, sicurezza, routing degli agenti e raccomandazioni.

**Motivazione**

Riduce prompt e chiamate LLM, rende il comportamento spiegabile e permette di
configurare logiche specifiche per dominio.

**Moduli coinvolti**

- nuovo `services/rule_engine.py`;
- configurazioni YAML/JSON;
- `DataValidatorAgent`;
- `DataProcessorAgent`;
- `ConversationAgent`;
- `Coordinator`.

**Priorita:** Alta.

**Dipendenza:** Knowledge Base consigliata, ma implementabile in parallelo.

### Milestone 8 - Statistic Engine avanzato

**Obiettivo**

Ampliare le analisi locali con distribuzioni, quantili, varianza, intervalli di
confidenza, test di ipotesi, correlazioni robuste, regressioni descrittive,
coorti e confronti tra gruppi.

**Motivazione**

Il motore attuale copre analisi descrittive di base. Un Senior Data Analyst deve
poter motivare differenze e significativita con metodi statistici espliciti.

**Moduli coinvolti**

- nuovo `services/statistic_engine.py`;
- `services/analysis_engine.py`;
- `services/autonomous_analyst.py`;
- `services/senior_data_analyst_engine.py`;
- dipendenze statistiche selezionate.

**Priorita:** Alta.

**Dipendenza:** Rule Engine per la selezione affidabile dei test.

### Milestone 9 - Anomaly Detection Engine

**Obiettivo**

Rilevare anomalie su valori, serie temporali, categorie, frequenze e qualita
dati con metodi robusti e configurabili.

**Motivazione**

La rilevazione corrente usa segnali descrittivi aggregati. Servono algoritmi
dedicati, soglie motivate, severita e spiegazioni verificabili.

**Moduli coinvolti**

- nuovo `services/anomaly_detection_engine.py`;
- Statistic Engine;
- `SeniorDataAnalystEngine`;
- grafici e report;
- Knowledge Base per soglie di business.

**Priorita:** Alta.

**Dipendenza:** Milestone 8.

### Milestone 10 - Predictive Analytics

**Obiettivo**

Introdurre forecast, classificazione, regressione e scoring con pipeline
riproducibili, validazione temporale e metriche esplicite.

**Motivazione**

Permette di passare dalla descrizione del passato alla previsione e al supporto
decisionale, senza presentare stime come certezze.

**Moduli coinvolti**

- nuovo `services/predictive_analytics.py`;
- model registry locale;
- feature engineering;
- sessioni e knowledge base;
- report con metriche e limiti del modello.

**Priorita:** Media.

**Dipendenza:** Statistic Engine, Anomaly Engine e sessioni persistenti.

### Milestone 11 - Auto Prompt Optimizer

**Obiettivo**

Versionare e ottimizzare automaticamente prompt e skill sulla base di test,
feedback ed esiti, senza modifiche incontrollate in produzione.

**Motivazione**

Finche alcuni provider LLM restano disponibili, i prompt devono diventare
asset misurabili, testabili e reversibili invece di stringhe statiche.

**Moduli coinvolti**

- nuovo `services/prompt_optimizer.py`;
- `skills/*/SKILL.md`;
- Learning Engine;
- benchmark e dataset di valutazione;
- registry/versioning dei prompt.

**Priorita:** Media.

**Dipendenza:** Learning Engine e Knowledge Base.

### Milestone 12 - Autonomia completa senza OpenAI

**Obiettivo**

Garantire l'intero flusso, dall'interpretazione iniziale al report e ai
follow-up, senza dipendenze obbligatorie da OpenAI.

**Motivazione**

Riduce costi, latenza, vincoli di rete e rischi di disponibilita; migliora
privacy e controllo.

**Moduli coinvolti**

- tutti gli agenti;
- motore locale di intent e slot extraction;
- text-to-SQL locale e schema graph;
- embedding locali;
- Rule Engine;
- Statistic e Anomaly Engine;
- Senior Data Analyst Engine;
- provider abstraction.

**Priorita:** Strategica.

**Dipendenza:** Tutte le milestone precedenti.

## Debito tecnico

- Il branch corrente e `main` e contiene le modifiche non committate della
  Milestone 4. Per uno sviluppo strutturato sarebbe preferibile lavorare su un
  feature branch.
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

- **Data:** 25 giugno 2026
- **Ora:** 23:41:45 CEST
- **Branch Git:** `main`
- **HEAD:** `c23e060 feat: add Senior Data Analyst Engine and project handover documentation`
- **Stato repository:** modificato, non staged e non committato; `main` e
  allineato a `origin/main` prima delle modifiche locali.
- **Modifiche locali principali:** Analysis Session Manager, test dedicati e
  aggiornamenti a README e memoria tecnica.
- **Numero test:** 70 superati.
- **Quality gate:** 70 test pytest superati; `python3 -m compileall .`
  completato; `git diff --check` superato. L'alias `python` non e disponibile
  nell'ambiente, quindi e stato usato l'interprete equivalente `python3`.
