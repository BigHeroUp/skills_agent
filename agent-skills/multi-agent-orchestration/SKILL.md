---
name: multi-agent-orchestration
description: Orchestrare piu agenti AI come sistema coordinato. Usa questa skill quando Codex deve suddividere il lavoro tra specialisti, definire routing e delega, gestire contesto condiviso e imporre handoff affidabili, aggregazione e risoluzione conflitti.
---

# Multi Agent Orchestration

## Definire La Topologia Di Orchestrazione

1. Definire un orchestratore con obiettivo globale e accountability finale.
2. Definire agenti specialisti con confini di dominio stretti.
3. Definire logica di routing per assegnazione task.
4. Definire handoff contract tra agenti.
5. Definire logica di sintesi per merge dell output finale.

## Usare Questo Contratto Minimo Agente

Per ciascun agente specificare:

- `role`
- `owned_decisions`
- `required_inputs`
- `output_schema`
- `stop_conditions`
- `escalation_conditions`

Rifiutare specialisti senza stop ed escalation conditions esplicite.

## Regole Di Routing E Delega

- Fare routing per intent e capability richieste, non casualmente.
- Delegare solo sotto-problemi atomici con criteri di completamento.
- Prevenire deleghe circolari con max handoff depth.
- Imporre budget globale di tempo e costo per run.

## Risoluzione Dei Conflitti

Quando gli output specialisti sono in conflitto:

1. Confrontare qualità e recency delle evidenze.
2. Preferire output policy-compliant.
3. Se irrisolto, attivare percorso di adjudication ed emettere nota di incertezza.

## Deliverable

Produrre:

1. Mappa topologica (orchestratore, specialisti, sintetizzatore).
2. Routing table.
3. Handoff schema.
4. Policy di failure e fallback.

## Riferimenti

- Caricare [references/orchestration-patterns.md](references/orchestration-patterns.md) per topologie, template handoff e anti-pattern.
