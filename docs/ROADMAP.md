# Skills Agent V2 Roadmap

## Roadmap Summary

La V2 evolve Skills Agent da pipeline di analisi locale a piattaforma
offline-first di Analytical Intelligence.

## Milestones

### Milestone 6 - Knowledge Reasoning Engine

- Status: completed
- Outcome: reasoning deterministico basato su casi simili, pattern riusabili e
  raccomandazioni analitiche.

### Milestone 7 - Knowledge Graph Governance & Quality

- Status: planned
- Focus:
  - validazione quality del grafo;
  - deduplicazione nodi;
  - policy di naming e relazioni;
  - controlli di coerenza e coverage.

### Milestone 8 - Experience Engine

- Status: planned
- Focus:
  - apprendimento deterministico dell'esperienza analitica;
  - ranking di strategie efficaci;
  - memoria delle spiegazioni piu utili;
  - calibrazione dei suggerimenti in base ai risultati storici.

### Milestone 9 - Recommendation Engine

- Status: planned
- Focus:
  - next best analytical action;
  - prioritizzazione raccomandazioni;
  - policy di suggerimento per contesto, dominio e rischio.

### Milestone 10 - Decision Intelligence Layer

- Status: planned
- Focus:
  - formalizzazione del decision core;
  - scoring evidenze;
  - arbitration tra strategie, anomalie, root cause e recommendation.

### Milestone 11 - Domain Pack Marketplace

- Status: planned
- Focus:
  - catalogo pack;
  - lifecycle dei pack;
  - validazione compatibilita;
  - distribuzione locale e offline.

### Milestone 12 - Optional LLM Narrative Layer

- Status: planned
- Focus:
  - sintesi executive;
  - riformulazione professionale;
  - spiegazioni naturali avanzate;
  - assistenza conversazionale non critica.

## Planning Rule

Ogni milestone futura deve rispettare tre vincoli:

- preservare il core offline-first;
- non spostare decisioni critiche su LLM;
- introdurre test riproducibili prima di considerare la milestone completata.
