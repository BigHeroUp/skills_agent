---
name: agent-discovery
description: Definisci le basi di un nuovo agente AI a partire da richieste vaghe. Usa questa skill quando Codex deve trasformare obiettivi di business in una specifica precisa con perimetro, input, output, guardrail, strumenti, criteri di successo e non-obiettivi prima dell implementazione.
---

# Agent Discovery

## Eseguire Il Workflow Di Discovery

1. Convertire la richiesta in un obiettivo primario e fino a tre obiettivi secondari.
2. Definire utenti, eventi di attivazione e frequenza di esecuzione.
3. Elencare input consentiti e output richiesti con formato esplicito.
4. Identificare vincoli: latenza, costo, privacy, compliance e soglie di qualità.
5. Definire non-obiettivi espliciti per evitare scope creep.
6. Produrre una specifica di handoff utilizzabile da prompt, tooling e valutazione.

## Produrre Questo Contratto Di Output

Restituire un unico blocco YAML con questa struttura:

```yaml
agent_name:
primary_objective:
secondary_objectives: []
users:
trigger_events: []
inputs:
  - name:
    required: true
    format:
outputs:
  - name:
    format:
    quality_bar:
constraints:
  latency_ms:
  cost_per_run:
  privacy_rules: []
  compliance_rules: []
non_goals: []
required_tools: []
acceptance_tests: []
risks: []
open_questions: []
```

## Quality Gates

- Rifiutare verbi ambigui come "migliorare" senza target misurabili.
- Rifiutare output senza formato e quality bar.
- Richiedere almeno tre acceptance test prima dell handoff.
- Collegare ogni rischio a un ipotesi di mitigazione.

## Riferimenti

- Caricare [references/discovery-template.md](references/discovery-template.md) per intake strutturato e conversione nel contratto YAML finale.
