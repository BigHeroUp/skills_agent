---
name: agent-ops-playbook
description: Gestisci agenti AI in produzione con procedure chiare di deployment, monitoraggio e incident response. Usa questa skill quando Codex deve preparare runbook per release readiness, osservabilità, alerting, rollback e postmortem.
---

# Agent Ops Playbook

## Checklist Pre-Rilascio

1. Verificare che versioni prompt e tool contract siano pin.
2. Verificare che i gate di valutazione siano passati sulla build corrente.
3. Verificare segreti, permessi e confini di accesso ai dati.
4. Verificare regole alert e copertura dashboard.
5. Definire trigger di rollback e owner on-call.

## Monitoraggio Runtime

Tracciare almeno:

- Success rate
- Refusal rate
- Conteggio policy violation
- Tool timeout rate
- P95 latency
- Costo per 100 run

## Workflow Incident Response

1. Classificare severità (SEV1-SEV3).
2. Stabilizzare riducendo blast radius (feature flag, rate limit, safe mode).
3. Diagnosticare root cause su prompt, tool o dati.
4. Mitigare con hotfix o rollback.
5. Verificare recupero con regressioni mirate.
6. Pubblicare postmortem con follow-up action.

## Deliverable

Produrre:

1. Deployment checklist.
2. Alert map con soglie.
3. Incident runbook.
4. Postmortem template.

## Riferimenti

- Caricare [references/ops-runbook-template.md](references/ops-runbook-template.md) per checklist e template operativi.
