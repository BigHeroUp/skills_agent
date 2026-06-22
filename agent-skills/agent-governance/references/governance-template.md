# Template Governance

## Matrice Ruoli

| Ruolo | Responsabilita Principali | Limiti | KPI |
|---|---|---|---|
| Owner |  |  |  |
| Reviewer |  |  |  |
| Operator |  |  |  |
| Auditor |  |  |  |

## Permission Matrix

| Action ID | Risk Level | Ruoli Consentiti | Approvazioni Richieste | Scope Dati | Rollback Owner |
|---|---|---|---|---|---|

## Regole Approval Gate

- Basso: nessuna approvazione, audit automatico.
- Medio: approvazione reviewer.
- Alto: doppia approvazione (reviewer + owner).
- Critico: approvazione owner + notifica auditor + finestra di monitoraggio.

## Schema Audit Log

```yaml
audit_event:
  event_id:
  request_id:
  agent_id:
  action_id:
  risk_level:
  requested_by:
  approved_by: []
  decision: approved|rejected|blocked
  decision_reason:
  policy_version:
  input_digest:
  output_digest:
  timestamp_utc:
```

## Template Escalation

- Trigger:
- Severita:
- Owner escalation:
- Tempo massimo risposta:
- Azione di contenimento:
- Criterio di chiusura:

## Checklist Compliance

- Principio least privilege verificato
- Separation of duties implementata
- Approval gate allineati al rischio
- Audit log completo e immutabile
- Processo eccezioni documentato
