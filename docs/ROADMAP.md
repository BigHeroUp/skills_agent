# Skills Agent V2 Roadmap

## Roadmap Summary

La V2 evolve Skills Agent da pipeline di analisi locale a piattaforma
offline-first di Analytical Intelligence.

## Milestones

### V2.2.0 - Analytical Experience Engine

- Status: completed
- Focus:
  - accumulate deterministic analytical experience from repeated analysis runs;
  - expose privacy-safe local experience storage;
  - add offline-first query and recommendation entrypoints over accumulated experience.

### V2.1.1 - Kernel Architecture Foundation

- Status: completed
- Focus:
  - stabilize the target kernel-oriented direction;
  - define capability-oriented architecture;
  - define domain model and development governance;
  - avoid runtime feature churn while architecture is being clarified.
- Note:
  this release does not introduce major runtime features; it formalizes the
  architectural direction for the next platform evolution stage.

### V2.1.4 - Kernel Analytical Parity

- Status: completed
- Focus:
  - capability Kernel `analysis.categorical_count` per conteggi, gruppi
    semantici e tabelle incrociate deterministiche;
  - provider registrato nel bootstrap sperimentale;
  - shadow runner per confrontare Kernel e motore analitico di produzione;
  - nessun cutover: il Coordinator resta il production boundary;
  - test di parità su fixture sintetiche neutrali.

### Milestone 6 - Knowledge Reasoning Engine

- Status: completed
- Outcome: reasoning deterministico basato su casi simili, pattern riusabili e
  raccomandazioni analitiche.

### Milestone 7A - Lossless Structural Validation

- Status: completed
- Focus:
  - lettura lossless del documento JSON raw;
  - validazione strutturale deterministica e non distruttiva;
  - report qualitativo JSON-safe;
  - modalita permissive e strict;
  - CLI locale read-only.

### Milestone 7B - Knowledge Graph Governance

- Status: completed
- Focus:
  - lifecycle completo di schema e governance policy;
  - cardinalita e deprecazioni;
  - estensioni controllate dai Domain Pack;
  - adozione read-only da parte dei consumer esistenti.

### Milestone 7C - Graph Lifecycle Foundation

- Status: completed
- Focus:
  - versionamento e migration registry;
  - repair esplicita, dry-run e auditabile;
  - persistence ports e compatibility facade;
  - write safety e backup espliciti.

### Milestone 8 - Knowledge Consistency

- Status: completed
- Focus:
  - regole semantiche deterministiche ed estendibili;
  - coerenza di metriche, confidence, periodi ed evidenze;
  - regole core e regole additive dei Domain Pack;
  - integrazione sicura con Experience e Recommendation.

### Milestone 9 - Recommendation Engine

- Status: completed
- Focus:
  - next best analytical action;
  - prioritizzazione raccomandazioni;
  - policy di suggerimento per contesto, dominio e rischio.

### Milestone 10 - Decision Intelligence Layer

- Status: completed
- Focus:
  - formalizzazione del decision core;
  - scoring evidenze;
  - arbitration tra strategie, anomalie, root cause e recommendation.

### Milestone 11 - Domain Pack Marketplace

- Status: completed
- Focus:
  - catalogo pack;
  - lifecycle dei pack;
  - validazione compatibilita;
  - distribuzione locale e offline.

### Milestone 12 - Optional LLM Narrative Layer

- Status: completed
- Focus:
  - sintesi executive;
  - riformulazione professionale;
  - spiegazioni naturali avanzate;
  - assistenza conversazionale non critica.

### Milestone 13 - Integrated Product Intelligence Flow

- Status: completed
- Focus:
  - orchestrazione post-analisi di governance, consistency ed experience;
  - ranking recommendation e arbitration decisionale end-to-end;
  - narrativa opzionale con report deterministico autoritativo;
  - payload unico su AgentContext e visibilità nella dashboard;
  - fallback non bloccante e test del Coordinator completo.

### Milestone 14 - Production Hardening and Observability

- Status: completed
- Focus:
  - CI GitHub obbligatoria per compilazione, dashboard smoke e test offline;
  - telemetria strutturata per ogni stage di Product Intelligence;
  - deadline, limiti di crescita e bounded concurrency configurabili;
  - persistenza atomica e transazioni locali sugli store JSON;
  - health check operativo e documentazione di produzione.

### Milestone 15 - Analysis Quality and Dashboard UX

- Status: completed
- Focus:
  - pipeline CSV senza errori di suggestion;
  - anomalie uniche con provenance multi-metodo;
  - report Markdown e tabelle leggibili;
  - card KPI/Product Intelligence e test end-to-end.

### Milestone 16 - Multi-user Data Foundation

- Status: completed
- Focus:
  - schema versionato per tenant, utenti e analisi;
  - SQLite offline e PostgreSQL production;
  - isolamento di risultati, Knowledge Graph ed Experience per tenant;
  - backup locale e strategia `pg_dump`.

### Milestone 17 - API, Authentication and Security

- Status: completed
- Focus:
  - REST API versionata e job asincroni bounded;
  - token firmati, password PBKDF2 e ruoli;
  - autorizzazione e isolamento tenant;
  - limiti request/record e security headers.

### Milestone 18 - Production Deployment

- Status: completed
- Focus:
  - container non-root;
  - PostgreSQL, API e dashboard con Gunicorn;
  - gateway Nginx, health check e metriche;
  - secrets esterni, backup e guida operativa.

### Milestone 19 - Integrated Portal and Durable Job Validation

- Status: completed
- Focus:
  - registrazione organizzazione, login e logout via portale;
  - upload CSV/Excel, storico tenant, progresso e annullamento;
  - Redis/RQ con worker separato e retry;
  - avvio Docker Desktop e collaudo reale PostgreSQL/Redis/Nginx;
  - workbook dimostrativi Sales e Operations verificati.

### Milestone 20 - Knowledge Intelligence Workspace

- Status: completed
- Focus:
  - command center autenticato e tenant-aware per tutta la memoria analitica;
  - grafo interattivo, filtri, inspector, lineage e provenance;
  - query deterministiche, Graph Quality/Governance ed Experience;
  - Recommendation, Decision e timeline nello stesso flusso di prodotto;
  - API read model ed export JSON autenticato.

### Milestone 21 - Unified Authenticated Product Entry

- Status: completed
- Focus:
  - un solo ingresso pubblico su `/portal` con redirect da `/`;
  - rimozione della modalità Dash anonima dal deployment;
  - tutte le analisi e la memoria vincolate a identità e tenant;
  - semplificazione del gateway e della topologia Docker.

### Milestone 22 - Risultati analitici visibili e localizzazione italiana

- Status: completed
- Focus:
  - flusso completo in italiano dalla registrazione al risultato;
  - aggiornamento automatico e pagina risultato per ogni job;
  - conteggi e raggruppamenti categoriali coerenti con la domanda business;
  - report scaricabile e accesso diretto al Knowledge Graph;
  - prevenzione dei report fuorvianti basati su zero record.

### Milestone 23 - Segmentazione categoriale multidimensionale

- Status: completed
- Focus:
  - tabelle incrociate tra la dimensione principale e le dimensioni correlate
    richieste dalla domanda business;
  - raggruppamenti semantici deterministici e spiegati, inclusa la composizione
    dei gruppi complementari richiesti in linguaggio naturale;
  - report answer-first, proporzionato al tipo di analisi e privo di metriche o
    sezioni non pertinenti;
  - test di quadratura e regressione basati su categorie e dimensioni neutrali.

### Milestone 24 - Kernel Analytical Parity

- Status: completed
- Focus:
  - esposizione della segmentazione categoriale tramite contratto Kernel;
  - confronto shadow automatico con il motore della pipeline corrente;
  - eventi e metadata Kernel preservati senza migrare il portale o i job;
  - promozione futura subordinata alla parità deterministica verificata.

### Milestone 25 - Private Beta Readiness

- Status: completed
- Focus:
  - quality gate deterministici e evidence-first;
  - feedback persistente, metriche aggregate e zero dati sensibili nelle label;
  - cancellazione, retention, backup e restore operativi;
  - probe bounded di carico/concorrenza e runbook incidenti;
  - nessuna dichiarazione di readiness senza il campione minimo richiesto.

## Planning Rule

Ogni milestone futura deve rispettare tre vincoli:

- preservare il core offline-first;
- non spostare decisioni critiche su LLM;
- introdurre test riproducibili prima di considerare la milestone completata.
