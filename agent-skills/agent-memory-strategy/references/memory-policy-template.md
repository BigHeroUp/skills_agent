# Template Policy Memoria

## Schema Memoria

```yaml
memory_record:
  memory_id:
  agent_id:
  user_id:
  memory_class: ephemeral_context|session_context|persistent_fact|user_preference|sensitive_data
  content:
  provenance:
  confidence:
  created_at_utc:
  last_verified_at_utc:
  ttl_days:
  deletion_policy:
```

## Regole Decisione Scrittura

Salvare memoria solo se tutte vere:

- Attesa di riuso in task futuri
- Effetto concreto sul comportamento agente
- Soglia di confidence sufficiente
- Categoria dati conforme a policy

## Template Ranking Retrieval

Esempio score:

`score = (intent_match * 0.45) + (recency * 0.25) + (confidence * 0.20) + (source_quality * 0.10)`

Vincoli:

- `top_k` default: 5-10
- Cap sul token budget della memoria richiamata
- Blocco hard su record scaduti o policy-restricted

## Policy Pruning

| Classe Memoria | TTL | Regola Pruning | Note |
|---|---|---|---|
| ephemeral_context | fine run | cancellazione immediata |  |
| session_context | fine sessione + grace | compattare in summary e cancellare raw |  |
| persistent_fact | review periodica | mantenere se verificata di recente |  |
| user_preference | TTL rolling | mantenere solo versione piu recente |  |
| sensitive_data | TTL minimo | cancellare o anonimizzare rapidamente |  |

## Verifiche Qualita

- Recall precision su benchmark task
- Tasso collisioni memoria contraddittoria
- Tasso uso memoria obsoleta
- Incidenti di over-retention dati sensibili

## Checklist Compliance

- Data minimization applicata
- TTL applicato automaticamente
- Flusso erase request documentato
- Access control e audit logging attivi
