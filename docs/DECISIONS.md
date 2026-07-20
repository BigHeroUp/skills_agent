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

## ADR-010: Raw graph document before normalized snapshot

- Status: accepted
- Context:
  `KnowledgeGraphStore.load()` converts JSON records into dictionaries keyed by
  node id and edge triple. This is useful for queries but hides duplicate ids,
  duplicate edges, malformed records, and incomplete fields before governance
  can inspect them.
- Decision:
  Structural validation must start from an immutable `RawGraphDocument` that
  preserves the original text, a SHA-256 fingerprint, parsing findings, and the
  raw record order. Normalized snapshots remain a downstream concern and are
  not introduced by Milestone 7A.
- Consequences:
  - duplicate and partial records remain observable;
  - future schema versions can be preserved without down-version writes;
  - validation can be read-only and fingerprint-addressable;
  - the legacy store remains available while adoption proceeds incrementally;
  - raw text must be retained in memory during validation.

## ADR-011: Separate structural validation, knowledge consistency, and repair

- Status: accepted
- Context:
  Graph syntax and referential integrity, analytical truth constraints, and
  corrective mutations have different risk and lifecycle requirements.
- Decision:
  Treat structural validation, future knowledge consistency, and future repair
  as separate services. Validation reports findings only. Repair is never run
  during read, load, validation, query, or reasoning and will require an
  explicit dry-run-first workflow in a later milestone.
- Consequences:
  - validation remains deterministic and non-destructive;
  - semantic rules can evolve without making the structural validator monolithic;
  - no current query or Coordinator behavior changes in Milestone 7A;
  - invalid data is quarantined explicitly rather than silently corrected;
  - migration, repair, and consistency remain out of scope until later milestones.

## ADR-012: Additive and namespaced Domain Pack graph extensions

- Status: accepted
- Context:
  I Domain Pack devono poter descrivere concetti specifici senza modificare o
  sovrascrivere silenziosamente lo schema core del Knowledge Graph.
- Decision:
  Le estensioni di schema sono additive, immutabili e associate a un solo
  `pack_id`. I node type usano il prefisso `<pack_id>__`; le relationship usano
  `<PACK_ID>__`. Collisioni, pack duplicati e riferimenti a node type sconosciuti
  rendono invalida la composizione della policy prima della validazione dati.
- Consequences:
  - lo schema core resta autoritativo e non viene mutato;
  - la provenienza delle estensioni è esplicita e deterministica;
  - più Domain Pack possono essere composti in ordine stabile;
  - rimozione, migration e repair restano operazioni future ed esplicite.

## ADR-013: Opt-in read-only governance adoption

- Status: accepted
- Context:
  I consumer esistenti usano lo store normalizzato e non possono essere migrati
  tutti insieme senza rischiare regressioni o blocchi su snapshot legacy.
- Decision:
  Introdurre una facade read-only con tre modalità: `legacy` mantiene il
  comportamento corrente senza validazione; `observe` valida e allega il report
  ma conserva lo snapshot legacy; `enforce` usa esclusivamente record accettati
  e blocca il consumo quando la policy strict non lo consente.
- Consequences:
  - il default resta retrocompatibile;
  - query, reasoning, experience e Kernel possono adottare governance in modo
    esplicito e incrementale;
  - lo stato qualitativo diventa osservabile senza introdurre scritture;
  - l'enforcement può essere attivato solo dopo aver misurato i grafi esistenti.

## ADR-014: Dry-run-first graph lifecycle with optimistic locking

- Status: accepted
- Context:
  Migration e repair modificano la memoria strutturata e devono evitare sia
  scritture accidentali sia la perdita di aggiornamenti concorrenti.
- Decision:
  Separare sempre pianificazione ed esecuzione. Un piano conserva il fingerprint
  raw di origine; l'esecuzione richiede conferma esplicita, backup obbligatorio e
  confronto ottimistico del fingerprint prima di una sostituzione atomica.
- Consequences:
  - validation e consumer non possono attivare write lifecycle;
  - ogni trasformazione applicata ha un id auditabile;
  - modifiche intervenute dopo il dry-run bloccano l'esecuzione;
  - i downgrade restano vietati e nessuna migration viene auto-registrata.

## ADR-015: Semantic consistency runs after structural admission

- Status: accepted
- Context:
  Un grafo strutturalmente valido può contenere confidence fuori scala,
  timestamp incoerenti o root cause prive di evidenza.
- Decision:
  Eseguire regole semantiche deterministiche solo sui record strutturalmente
  accettati. Le regole core e quelle additive dei Domain Pack hanno id unici;
  gli errori chiudono esplicitamente i gate verso Experience e Recommendation.
- Consequences:
  - struttura e verità analitica restano responsabilità separate;
  - grafi non consumabili non vengono valutati semanticamente;
  - warning semantici restano osservabili ma non bloccanti;
  - nessuna regola di consistency modifica o ripara il grafo.

## ADR-016: Recommendations rank explicit evidence-backed candidates

- Status: accepted
- Context:
  Le next best action devono essere riproducibili e filtrate per rischio,
  dominio e contesto prima di influenzare decisioni analitiche.
- Decision:
  Il Recommendation Engine riceve candidati espliciti con provenienza e applica
  prima admission policy, poi ranking pesato e penalità di rischio. Un gate di
  consistency chiuso impedisce ogni raccomandazione.
- Consequences:
  - il ranking è stabile, versionato e spiegabile;
  - Experience è una fonte di candidati, non l'autorità finale;
  - azioni fuori dominio o troppo rischiose vengono registrate come rifiutate;
  - nessun LLM decide priorità o ammissibilità.

## ADR-017: Decision arbitration must be evidence-addressable

- Status: accepted
- Context:
  Strategie, anomalie, root cause e recommendation possono proporre azioni in
  competizione con confidence e rischi differenti.
- Decision:
  Ogni opzione decisionale deve riferire evidence id espliciti. Il Decision Core
  applica una policy versionata a confidence, completezza delle evidenze,
  priorità della fonte e rischio, selezionando o astenendosi.
- Consequences:
  - ogni decisione è riproducibile e collegata alle evidenze usate;
  - evidenze mancanti riducono il punteggio e restano visibili;
  - opzioni non supportate vengono rifiutate;
  - selezione ed esecuzione dell'azione restano responsabilità separate.

## ADR-018: Domain Pack distribution is local, verified, and non-overwriting

- Status: accepted
- Context:
  I Domain Pack devono essere distribuibili in ambienti offline senza affidarsi
  a un marketplace remoto o a installazioni non verificabili.
- Decision:
  Distribuire bundle locali con inventario e checksum SHA-256. Verificare
  compatibilità e path safety prima dell'installazione, validare in staging e
  spostare atomicamente solo con conferma esplicita. Non sovrascrivere pack già
  installati.
- Consequences:
  - catalogo e distribuzione funzionano senza rete;
  - bundle corrotti o con path traversal vengono rifiutati;
  - install, update e remove restano lifecycle distinti;
  - la provenienza del bundle è verificabile tramite checksum complessivo.

## ADR-019: LLM narrative never becomes an analytical authority

- Status: accepted
- Context:
  Sintesi e riformulazione naturale migliorano l'esperienza, ma non devono
  alterare fatti, ranking o decisioni prodotte dal core deterministico.
- Decision:
  Il layer narrativo è disabilitato per default, riceve solo contenuto e fatti
  espliciti, mantiene sempre il testo deterministico come fonte autoritativa e
  blocca usi critici. Ogni errore restituisce il fallback esatto.
- Consequences:
  - il prodotto resta pienamente utile offline;
  - l'uso del modello e la sua provenienza sono visibili;
  - dati raw comuni vengono esclusi prima della chiamata;
  - LLM non valida, raccomanda, arbitra o esegue azioni.

## ADR-020: Product intelligence is a non-blocking post-analysis stage

- Status: accepted
- Context:
  Governance, consistency, experience, recommendation, decision e narrative
  esistevano come servizi modulari ma non formavano ancora un unico percorso di
  prodotto visibile nella pipeline e nella dashboard.
- Decision:
  Eseguire un `ProductIntelligenceAgent` dopo la persistenza del Knowledge Graph.
  L'agente orchestra i servizi in ordine, pubblica un solo payload su
  `AgentContext` e non sostituisce report o risultati deterministici. Errori del
  layer restano non bloccanti per l'analisi principale.
- Consequences:
  - ogni analisi completa attraversa lo stesso flusso di intelligence;
  - gate e provenienza restano visibili end-to-end;
  - la dashboard espone la decisione senza eseguirla;
  - il Coordinator resta il production boundary finché il Kernel è sperimentale.

## ADR-021: Local production state uses bounded atomic execution

- Status: accepted
- Context:
  La dashboard può avviare analisi concorrenti e gli store JSON locali non
  devono perdere aggiornamenti, lasciare file parziali o crescere senza limite.
- Decision:
  Serializzare per path i cicli read-modify-write, persistere tramite temporary
  file e atomic replace, limitare dimensioni e workload da configurazione e
  ammettere un solo Product Intelligence flow per grafo con attesa bounded.
  Pubblicare metriche di stage nel payload oltre che nei log.
- Consequences:
  - un errore di scrittura preserva lo snapshot precedente;
  - la contesa diventa un errore osservabile ma non blocca l'analisi principale;
  - i limiti possono essere adattati per ambiente senza cambiare codice;
  - le deadline sono soft e non cancellano thread durante operazioni locali.
