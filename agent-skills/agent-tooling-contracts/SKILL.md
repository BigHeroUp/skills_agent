---
name: agent-tooling-contracts
description: Definisci interfacce tool robuste per agenti AI. Usa questa skill quando Codex deve specificare contratti tool, schema input/output, timeout, retry, idempotenza ed error semantics per rendere l esecuzione prevedibile e testabile.
---

# Agent Tooling Contracts

## Eseguire Un Workflow Contract-First

1. Elencare ogni tool richiamabile dall agente.
2. Definire schema input rigido con campi obbligatori e validazioni.
3. Definire schema output rigido e semantica della confidence.
4. Definire failure mode e codici errore normalizzati.
5. Definire policy di retry, timeout e idempotenza.
6. Definire campi di osservabilità per tracing.

## Regole Dei Contratti

- Preferire enum espliciti a stati testuali liberi.
- Usare timestamp ISO 8601 UTC.
- Includere `request_id` e `tool_call_id` per tracciabilità.
- Restituire errori machine-parseable con codici stabili.
- Distinguere errori retriable e non-retriable.

## Deliverable

Per ogni tool, produrre una sezione con:

- Purpose
- Input schema
- Output schema
- Error schema
- Retry e timeout policy
- Esempio valido e caso di failure

## Riferimenti

- Caricare [references/tool-contract-template.md](references/tool-contract-template.md) e compilare una sezione per tool.
