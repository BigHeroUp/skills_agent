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
- Status: planned
- Criteri completamento:
  - deduplicazione controllata;
  - naming convention relazioni;
  - quality checks su coverage e coerenza;
  - report di salute del grafo.
- Test attesi:
  - integrita snapshot;
  - assenza di collisioni critiche;
  - relazioni richieste presenti per ogni run valida.

## Milestone 8 - Experience Engine

- Obiettivo:
  rendere esplicito l'apprendimento dell'esperienza analitica.
- Status: planned
- Criteri completamento:
  - memoria di strategie efficaci;
  - outcome tracking locale;
  - scoring storico delle raccomandazioni;
  - regole di promozione/declassamento esperienza.
- Test attesi:
  - update score riproducibile;
  - comportamento stabile con storico vuoto;
  - export JSON-safe.

## Milestone 9 - Recommendation Engine

- Obiettivo:
  produrre next best analytical actions prioritizzate.
- Status: planned
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
- Status: planned
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
- Status: planned
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
- Status: planned
- Criteri completamento:
  - sintesi executive opzionale;
  - riformulazione professionale;
  - spiegazioni naturali assistite;
  - chat avanzata non critica.
- Test attesi:
  - funzionamento completo anche con LLM disattivato;
  - nessun impatto sui risultati fattuali;
  - fallback locale leggibile.
