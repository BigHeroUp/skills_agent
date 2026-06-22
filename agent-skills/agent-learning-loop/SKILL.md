---
name: agent-learning-loop
description: Migliora continuamente le performance degli agenti dai risultati reali di esecuzione. Usa questa skill quando Codex deve analizzare log, failure e feedback, trovare difetti ricorrenti, proporre miglioramenti controllati e rilasciare update validati che migliorano altri agenti.
---

# Agent Learning Loop

## Eseguire Il Ciclo Di Apprendimento

1. Raccogliere outcome da produzione e valutazione.
2. Raggruppare i failure per tipologia di difetto.
3. Prioritizzare opportunità di miglioramento per impatto e frequenza.
4. Generare modifiche mirate su prompt, tool contract o policy.
5. Validare i miglioramenti rispetto alla baseline.
6. Rilasciare solo se i gate passano e non emergono regressioni critiche.

## Contratto Dati Di Apprendimento

Per ogni run catturare:

- `agent_id`
- `task_type`
- `input_fingerprint`
- `output_result`
- `error_type`
- `user_feedback`
- `latency_ms`
- `cost`

## Policy Di Miglioramento

- Non applicare riscritture ampie del prompt per incidenti isolati.
- Preferire modifiche minime collegate a un cluster di failure specifico.
- Richiedere almeno un test di regressione per ogni change proposta.
- Tenere changelog con causa, ipotesi e outcome misurato.

## Workflow Upgrade Cross-Agent

1. Rilevare difetti comuni su piu agenti.
2. Estrarre pattern di fix riusabili.
3. Applicare fix in canary mode su subset agenti.
4. Confrontare metriche canary vs control.
5. Promuovere fix solo dopo finestra di stabilita.

## Deliverable

Produrre:

1. Failure taxonomy.
2. Backlog miglioramenti prioritizzato.
3. Proposte patch per agente impattato.
4. Validation report con decisione go/no-go.

## Riferimenti

- Caricare [references/learning-loop-template.md](references/learning-loop-template.md) per taxonomy, modello di priorita e rollout template.
