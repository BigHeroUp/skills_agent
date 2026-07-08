# Architectural Decision Records

## ADR-001: JSON Knowledge Graph before graph database

- Status: accepted
- Context:
  Il progetto necessita di una memoria strutturata locale per run analitiche,
  colonne, anomalie, root cause e report, ma introdurre subito un graph database
  aumenterebbe complessita operativa, dipendenze e vincoli di deployment.
- Decision:
  Usare uno snapshot JSON locale come Knowledge Graph iniziale, con nodi, archi,
  id stabili e schema serializzabile.
- Consequences:
  - deployment semplice e offline-friendly;
  - facile audit e debug;
  - query deterministiche locali;
  - possibile futura migrazione a graph database tramite adapter dedicato.

## ADR-002: Deterministic reasoning before LLM reasoning

- Status: accepted
- Context:
  Il reasoning del core analitico deve essere verificabile, stabile e
  riproducibile anche senza accesso a modelli esterni.
- Decision:
  Introdurre prima motori di reasoning rule-based e statistici, lasciando agli
  LLM un ruolo opzionale e non critico.
- Consequences:
  - maggiore auditabilita;
  - minor rischio di allucinazioni;
  - maggiore robustezza offline;
  - necessaria maggiore disciplina nel disegno di regole e scoring.

## ADR-003: Offline-first analytical core

- Status: accepted
- Context:
  La piattaforma deve poter operare in ambienti con rete limitata, policy
  restrittive o requisiti di privacy elevati.
- Decision:
  Definire il core della piattaforma come offline-first, con pipeline,
  planning, statistical engine, knowledge layer e reasoning layer eseguibili
  localmente.
- Consequences:
  - maggiore controllo sui dati;
  - migliore compatibilita con ambienti enterprise;
  - dipendenza ridotta da servizi remoti;
  - maggiore investimento architetturale sui componenti locali.

## ADR-004: LLM as optional narrative layer

- Status: accepted
- Context:
  Gli LLM sono utili per spiegazione, sintesi e stile, ma non sono sufficienti
  come base affidabile per risultati analitici critici.
- Decision:
  Trattare gli LLM come layer opzionale per narrativa, executive summary,
  riformulazione linguistica e assistenza conversazionale avanzata.
- Consequences:
  - i report restano utili anche senza OpenAI;
  - i risultati numerici restano verificabili;
  - le chiamate LLM possono essere disattivate senza bloccare il prodotto;
  - va mantenuta una chiara separazione tra contenuto fattuale e testo narrativo.

## ADR-005: Experience Engine as deterministic learning layer

- Status: accepted
- Context:
  Il progetto deve accumulare esperienza analitica utile, ma senza demandare a
  LLM l'apprendimento implicito di strategie e decisioni.
- Decision:
  Introdurre un futuro Experience Engine deterministico, basato su feedback,
  pattern efficaci, outcome e raccomandazioni storiche.
- Consequences:
  - memoria esperienziale auditabile;
  - apprendimento incrementale locale;
  - compatibilita con governance e quality gate;
  - maggiore valore cumulativo del prodotto nel tempo.

## ADR-006: Kernel-oriented architecture

- Status: accepted
- Context:
  The current Coordinator model is effective for the present runtime, but it is
  not the long-term boundary for a multi-surface analytical platform.
- Decision:
  Adopt a kernel-oriented target architecture in which a Veraxis Kernel becomes
  the runtime orchestration boundary for capabilities, memory, reasoning, and
  decision services.
- Consequences:
  - clearer system boundaries;
  - better extensibility across UI, CLI, API, and SDK surfaces;
  - easier isolation of orchestration policy from execution roles;
  - need for explicit contracts and staged migration.

## ADR-007: Capability-oriented design

- Status: accepted
- Context:
  Pipeline-centric growth makes reuse harder and increases coupling between
  workflow actors and concrete services.
- Decision:
  Move platform evolution toward capability-oriented design, where analytical
  functions are exposed as reusable platform primitives.
- Consequences:
  - increased reuse;
  - better testability of analytical functions;
  - cleaner future kernel orchestration;
  - more up-front design work on interfaces and contracts.

## ADR-008: Event-driven evolution path

- Status: accepted
- Context:
  Veraxis does not need a distributed event platform today, but it does need a
  path toward richer lifecycle orchestration and traceable state transitions.
- Decision:
  Define an event-driven evolution path through explicit event contracts, while
  keeping the current runtime offline-first and local.
- Consequences:
  - future extensibility without immediate infrastructure complexity;
  - improved lifecycle traceability;
  - easier future decoupling between orchestration and execution;
  - need for disciplined event semantics.

## ADR-009: Agents must depend on abstractions, not concrete engines

- Status: accepted
- Context:
  Direct dependency from agents to concrete engines increases coupling and makes
  kernel transition harder.
- Decision:
  Future agent evolution must prefer abstractions, capability contracts, memory
  interfaces, and kernel-issued context over direct knowledge of concrete engine
  implementations.
- Consequences:
  - improved replaceability and maintainability;
  - cleaner orchestration boundaries;
  - easier testing and staged migration;
  - requirement to invest in interface design before heavy feature expansion.
