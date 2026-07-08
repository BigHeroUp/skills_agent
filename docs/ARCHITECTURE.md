# Skills Agent V2 Architecture

## Overview

Skills Agent V2 e organizzato in sei macro-layer, pensati per separare
orchestrazione, conoscenza, intelligence, decisione, apprendimento ed esperienza
utente.

L'obiettivo e mantenere il core analitico deterministico e offline-first,
consentendo ai layer superiori di aggiungere esperienza, spiegazioni e canali
senza compromettere auditabilita e riproducibilita.

## 1. Core Platform

### Responsabilita

- orchestrazione pipeline multi-agent;
- gestione contesto condiviso;
- data ingestion da CSV, Excel e Oracle;
- validazione base, processing, logging e runtime state;
- gestione UI locale e CLI locale.

### Moduli gia esistenti

- `coordinator.py`
- `utils/context.py`
- `services/analysis_service.py`
- `agents/data_source_manager.py`
- `agents/data_extractor.py`
- `agents/data_validator.py`
- `agents/data_processor.py`
- `ui/`
- `connectors/`

### Moduli futuri

- runtime profile manager;
- configuration registry V2;
- offline execution profiles;
- packaging e deployment profiles per ambienti air-gapped.

### Dipendenze

- pandas, openpyxl, oracledb;
- servizi locali del progetto;
- filesystem locale;
- Dash per la experience locale.

### Cosa deve rimanere deterministico

- ordine pipeline;
- costruzione `AgentContext`;
- validazioni base;
- trasformazioni dati;
- gestione errori e fallback locali.

## 2. Knowledge Platform

### Responsabilita

- persistenza e interrogazione della memoria analitica;
- rappresentazione esplicita di dataset, run, colonne, insight, anomalie e root cause;
- supporto a query locali e lineage.

### Moduli gia esistenti

- `services/knowledge_graph/store.py`
- `services/knowledge_graph/models.py`
- `services/knowledge_graph/query_engine.py`
- `services/knowledge_graph/analysis_mapper.py`
- `services/knowledge_graph/code_indexer.py`
- `services/knowledge_graph/analysis_comparator.py`

### Moduli futuri

- governance layer del Knowledge Graph;
- quality checker per nodi e relazioni;
- schema evolution manager;
- eventuale adapter per graph database, senza cambiare il core.

### Dipendenze

- snapshot JSON locale;
- mapping dal `AgentContext`;
- query deterministiche sullo snapshot.

### Cosa deve rimanere deterministico

- id stabili;
- serializzazione JSON-safe;
- query rule-based;
- confronto tra run;
- filtri su nodi, archi e lineage.

## 3. Intelligence Platform

### Responsabilita

- pianificazione analitica;
- analisi statistiche;
- anomaly detection;
- root cause analysis;
- reasoning su casi simili e pattern ricorrenti.

### Moduli gia esistenti

- `services/analysis_engine.py`
- `services/analytical_planning_engine.py`
- `services/analytical_intent_planner.py`
- `services/analytical_reasoning_layer.py`
- `services/advanced_statistical_engine.py`
- `services/anomaly_detection_engine.py`
- `services/root_cause_analysis_engine.py`
- `services/knowledge_graph/reasoning_engine.py`

### Moduli futuri

- Experience Engine;
- Recommendation Engine;
- Decision Intelligence Layer;
- scenario comparison engine;
- evidence scoring layer.

### Dipendenze

- dataframe reale;
- metadata e semantic roles;
- Knowledge Platform;
- Domain Packs.

### Cosa deve rimanere deterministico

- scelta delle analisi;
- scoring e ranking delle priorita;
- statistiche;
- rilevazione anomalie;
- reasoning esperienziale;
- raccomandazioni operative basate su evidenze.

## 4. Decision Platform

### Responsabilita

- traduzione dell'intelligence in next best analytical actions;
- prioritizzazione di passi analitici e decisioni;
- gestione dei tradeoff tra evidenza, confidenza e rischio operativo.

### Moduli gia esistenti

- `services/analytical_reasoning_layer.py`
- `services/knowledge_graph/reasoning_engine.py`
- `services/root_cause_analysis_engine.py`

### Moduli futuri

- Decision Intelligence Layer completo;
- policy engine;
- evidence arbitration;
- recommendation prioritization engine.

### Dipendenze

- Intelligence Platform;
- Learning Platform;
- Domain Packs;
- governance rules.

### Cosa deve rimanere deterministico

- ranking delle raccomandazioni;
- scoring di confidence;
- selezione di next steps;
- decisioni analitiche critiche.

## 5. Learning Platform

### Responsabilita

- apprendimento locale da feedback, uso e risultati;
- promozione/declassamento pattern;
- affidabilita delle strategie;
- accumulo di esperienza auditabile.

### Moduli gia esistenti

- `services/learning_engine.py`
- `services/pattern_knowledge_engine.py`
- `services/analysis_session_manager.py`
- `utils/analysis_history_manager.py`
- `utils/query_history_manager.py`

### Moduli futuri

- Experience Engine deterministico;
- skill performance memory;
- feedback quality calibrator;
- recommendation outcome tracker.

### Dipendenze

- eventi locali;
- session history;
- risultati deterministici;
- Knowledge Platform.

### Cosa deve rimanere deterministico

- update dei punteggi;
- audit trail;
- promozione pattern;
- riuso esperienze precedenti;
- scoring di utilita storica.

## 6. Experience Platform

### Responsabilita

- esperienza utente locale;
- report professionali;
- chat di follow-up;
- dashboard, timeline e visualizzazioni;
- integrazione opzionale con layer narrativi.

### Moduli gia esistenti

- `ui/layout.py`
- `ui/callbacks.py`
- `agents/analyst.py`
- `agents/report_generator.py`
- `services/senior_data_analyst_engine.py`
- `utils/chart_generator.py`
- `utils/pdf_generator.py`

### Moduli futuri

- Experience Engine UI-aware;
- workspace memory per utente;
- explanation composer multi-canale;
- marketplace di Domain Pack;
- optional advanced chat layer.

### Dipendenze

- Core Platform;
- Intelligence Platform;
- output deterministici;
- eventuale LLM narrativo opzionale.

### Cosa deve rimanere deterministico

- contenuto fattuale dei report;
- KPI, trend, anomalie e root cause riportati;
- visualizzazioni guidate dai dati reali;
- fallback locale in assenza di LLM.

## Cross-Layer Rule

Gli LLM possono arricchire spiegazione, tono, chiarezza e presentazione, ma non
devono sostituire:
- reasoning core;
- scoring analitico;
- selezione delle analisi;
- evidenze statistiche;
- decisioni critiche.

## Target Architecture: Kernel-Oriented Veraxis

The current document describes the V2 layer model already used to organize the
platform direction.

The next architectural step is a **Kernel-Oriented Veraxis** target model that
separates kernel orchestration, capabilities, events, memory, knowledge,
reasoning, inference, decision, learning, domain specialization, and interface
surfaces more explicitly.

Reference documents:

- [Veraxis Kernel-Oriented Architecture](VERAXIS_ARCHITECTURE.md)
- [Veraxis Domain Model](VERAXIS_DOMAIN_MODEL.md)
- [Veraxis Development Guide](VERAXIS_DEVELOPMENT_GUIDE.md)
- decisioni critiche.
