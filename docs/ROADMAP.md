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

- Status: in progress
- Focus:
  - stabilize the target kernel-oriented direction;
  - define capability-oriented architecture;
  - define domain model and development governance;
  - avoid runtime feature churn while architecture is being clarified.
- Note:
  this release does not introduce major runtime features; it formalizes the
  architectural direction for the next platform evolution stage.

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

## Planning Rule

Ogni milestone futura deve rispettare tre vincoli:

- preservare il core offline-first;
- non spostare decisioni critiche su LLM;
- introdurre test riproducibili prima di considerare la milestone completata.
