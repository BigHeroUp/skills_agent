# Skills Agent V2 Milestones

## Reading Guide

Ogni milestone documenta:

- obiettivo;
- status;
- criteri di completamento;
- test attesi.

## Milestone 6 - Knowledge Reasoning Engine

- Obiettivo:
  trasformare il Knowledge Graph da archivio interrogabile a motore di reasoning
  esperienziale locale.
- Status: completed
- Criteri completamento:
  - profiling sintetico da `AgentContext`;
  - similar run detection deterministica;
  - reusable pattern extraction;
  - raccomandazioni analitiche locali;
  - integrazione in pipeline senza rompere la dashboard;
  - sezione report opzionale e conservativa.
- Test attesi:
  - KG vuoto;
  - current profile vuoto;
  - dataframe assente o vuoto;
  - ordinamento per score;
  - score nel range 0..1;
  - failure agent non invalida il context.

## Milestone 7 - Knowledge Graph Governance & Quality

- Obiettivo:
  migliorare qualita, consistenza e governance del grafo locale.
- Status: completed
- Criteri completamento:
  - deduplicazione controllata;
  - naming convention relazioni;
  - quality checks su coverage e coerenza;
  - report di salute del grafo.
- Test attesi:
  - integrita snapshot;
  - assenza di collisioni critiche;
  - relazioni richieste presenti per ogni run valida.

## Milestone 8 - Knowledge Consistency

- Obiettivo:
  proteggere Experience e Recommendation da conoscenza semanticamente incoerente.
- Status: completed
- Criteri completamento:
  - regole semantiche core;
  - regole additive dei Domain Pack;
  - gate espliciti verso Experience e Recommendation;
  - report JSON-safe e deterministico.
- Test attesi:
  - update score riproducibile;
  - comportamento stabile con storico vuoto;
  - export JSON-safe.

## Milestone 9 - Recommendation Engine

- Obiettivo:
  produrre next best analytical actions prioritizzate.
- Status: completed
- Criteri completamento:
  - generazione raccomandazioni per contesto e dominio;
  - priorita esplicite;
  - motivazioni basate su evidenze e memoria.
- Test attesi:
  - ranking deterministico;
  - fallback con evidenze insufficienti;
  - massimo rumore narrativo.

## Milestone 10 - Decision Intelligence Layer

- Obiettivo:
  formalizzare il decision core della piattaforma.
- Status: completed
- Criteri completamento:
  - arbitration tra evidenze;
  - scoring di confidenza;
  - integrazione tra reasoning, anomaly e root cause.
- Test attesi:
  - nessuna decisione critica solo su testo;
  - scoring stabile e tracciabile;
  - output auditabile.

## Milestone 11 - Domain Pack Marketplace

- Obiettivo:
  trasformare i Domain Pack in capability distribuibili.
- Status: completed
- Criteri completamento:
  - discovery pack;
  - policy di compatibilita;
  - metadata di qualita e versione;
  - installazione e uso locale.
- Test attesi:
  - validazione schema pack;
  - compatibilita backward;
  - fallback se pack mancante o invalido.

## Milestone 12 - Optional LLM Narrative Layer

- Obiettivo:
  aggiungere un layer narrativo avanzato senza spostare il core decisionale.
- Status: completed
- Criteri completamento:
  - sintesi executive opzionale;
  - riformulazione professionale;
  - spiegazioni naturali assistite;
  - chat avanzata non critica.
- Test attesi:
  - funzionamento completo anche con LLM disattivato;
  - nessun impatto sui risultati fattuali;
  - fallback locale leggibile.

## Milestone 13 - Integrated Product Intelligence Flow

- Obiettivo:
  trasformare i servizi di intelligence in un singolo percorso prodotto.
- Status: completed
- Criteri completamento:
  - orchestrazione dopo la persistenza del Knowledge Graph;
  - gate consistency applicati a Experience, Recommendation e Decision;
  - payload unico su `AgentContext`;
  - decisione visibile nella dashboard senza esecuzione automatica;
  - narrativa opt-in e report deterministico preservato;
  - failure del layer non bloccante per l'analisi principale.
- Test attesi:
  - percorso completo attraverso `Coordinator.run()`;
  - fallback con narrativa disabilitata;
  - decisione e provenance esposte;
  - report finale invariato;
  - disabilitazione per singola analisi.

## Milestone 14 - Production Hardening and Observability

- Obiettivo:
  rendere il flusso integrato operabile e protetto in esecuzioni concorrenti.
- Status: completed
- Criteri completamento:
  - CI riproducibile su GitHub Actions;
  - metriche per stage incluse nel payload e nei log rotanti;
  - limiti configurabili per input, candidati, storico e persistenza;
  - write atomiche e read-modify-write serializzato per path;
  - health check CLI e dashboard smoke test.
- Test attesi:
  - timeout e lock contention osservabili;
  - snapshot precedente preservato quando un limite viene superato;
  - dashboard costruibile senza avviare il server;
  - regressione offline completa.

## Milestones 15–19 - Productization

- Status: completed
- Milestone 15: qualità analitica, deduplicazione multi-metodo, Markdown e card dashboard.
- Milestone 16: persistenza versionata e tenant-aware su SQLite/PostgreSQL.
- Milestone 17: API REST, autenticazione firmata, RBAC e job asincroni bounded.
- Milestone 18: Docker non-root, Gunicorn, Nginx, health, metrics, secrets e backup.
- Milestone 19: portale account, upload CSV/Excel, storico/progresso/cancel, Redis/RQ e collaudo PostgreSQL reale.
- Test attesi:
  - pipeline CSV end-to-end senza regressione QuerySuggestion;
  - isolamento della stessa analysis id tra tenant;
  - viewer senza diritto di avviare job;
  - readiness database e metriche operative;
  - configurazioni compilabili e documentate.

## Milestone 20 - Knowledge Intelligence Workspace

- Status: completed
- Workspace autenticato `/portal/knowledge` con visual language JARVIS-inspired.
- Grafo SVG tenant-scoped con ricerca, filtro per tipo, zoom, legenda e relazioni dominanti.
- Inspector con proprietà, connessioni e provenance dei nodi reali.
- Query console deterministica collegata al `KnowledgeGraphQueryEngine` offline-first.
- Graph Quality/Governance, Analytical Experience, Recommendation, Decision e timeline nello stesso flusso.
- API Bearer `GET /api/v1/knowledge` e `POST /api/v1/knowledge/query`, più export JSON autenticato.
- Stati empty/loading/error e richieste bounded fino a 1.000 nodi.
- Test: isolamento tenant, accesso protetto, query, export e rendering del workspace.
