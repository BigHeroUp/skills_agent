# Pattern Orchestrazione

## Pattern Di Topologia

- Hub-and-spoke: un orchestratore delega a piu specialisti.
- Pipeline: sequenza deterministica di specialisti.
- Adjudication: due specialisti piu un tie-breaker.
- Parallel fan-out/fan-in: split task indipendenti e merge finale.

## Template Routing Table

| Intent | Capability Richiesta | Agente | Agente Fallback | Max Retry |
|---|---|---|---|---|

## Template Handoff Schema

```yaml
handoff:
  from_agent:
  to_agent:
  task_id:
  objective:
  required_output_schema:
  context_summary:
  constraints:
    latency_ms:
    budget:
  done_definition:
```

## Regole Di Aggregazione

- Normalizzare tutti gli output specialisti su uno schema comune prima del merge.
- Preservare source attribution per ogni claim.
- Esplicitare conflitti irrisolti invece di sovrascrivere in silenzio.

## Anti-Pattern

- Scope specialisti sovrapposti.
- Nessun ownership della decisione finale.
- Handoff free-form senza schema.
- Delega senza controlli di budget.
