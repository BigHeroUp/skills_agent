# Offline-First Strategy

## Principle

Skills Agent V2 adotta una strategia offline-first:

- il core analitico deve funzionare senza API OpenAI;
- gli LLM sono opzionali;
- nessuna decisione analitica critica deve dipendere esclusivamente da un LLM.

## Core Offline / Deterministico

I seguenti componenti appartengono al core offline-first:

- Knowledge Graph
- Query Engine
- Reasoning Engine
- Statistical Engine
- Analytical Planning Engine
- Experience Engine futuro
- Recommendation Engine futuro

## Responsabilita del Core

Il core deterministico deve coprire:

- acquisizione e profiling dati;
- pianificazione delle analisi;
- selezione metriche e segmentazioni;
- statistiche e confronti;
- anomaly detection;
- root cause analysis;
- reasoning su casi simili;
- raccomandazioni analitiche;
- apprendimento locale e memoria esperienziale.

## LLM Opzionale

Gli LLM possono essere usati solo come supporto opzionale per:

- spiegazioni naturali;
- report narrativi;
- sintesi executive;
- riformulazione linguistica;
- assistenza chat avanzata.

## Hard Rule

Nessuna decisione analitica critica deve dipendere esclusivamente da un LLM.

In pratica significa che un LLM non puo essere l'unica fonte per:

- scegliere una metrica primaria;
- dichiarare un'anomalia;
- proporre una root cause fattuale;
- definire un ranking di evidenze;
- produrre una recommendation critica senza supporto deterministico.

## Design Consequences

- il prodotto deve restare utile anche con OpenAI disattivato;
- i report devono poter essere generati localmente;
- la UI non deve collassare in assenza di LLM;
- i layer narrativi devono poter essere disabilitati senza effetti sul core.
