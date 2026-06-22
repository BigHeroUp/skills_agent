---
name: agent-governance
description: Definisci la governance end-to-end di agenti AI con policy, ruoli, permessi, approval gate e audit trail. Usa questa skill quando Codex deve stabilire chi puo fare cosa, quando serve approvazione umana, come tracciare decisioni e come gestire escalation e accountability.
---

# Agent Governance

## Definire Il Modello Di Governance

1. Definire ruoli (owner, reviewer, operator, auditor).
2. Mappare responsabilita decisionali per ogni ruolo.
3. Definire matrice permessi per azioni e dati.
4. Definire gate di approvazione per azioni ad alto rischio.
5. Definire audit trail obbligatorio per decisioni e modifiche.

## Principi Obbligatori

- Least privilege per accesso a tool, dati e azioni.
- Separation of duties tra chi propone e chi approva.
- Human-in-the-loop per operazioni ad alto impatto.
- Tracciabilita completa di input, decisione, output e autore.

## Permission Model

Per ogni azione definire:

- `action_id`
- `risk_level` (basso, medio, alto, critico)
- `allowed_roles`
- `required_approvals`
- `data_scope`
- `rollback_owner`

Rifiutare qualsiasi azione senza ruolo autorizzato e policy esplicita.

## Approval Workflow

1. Classificare il rischio dell azione richiesta.
2. Verificare policy e prerequisiti.
3. Richiedere approvazione se il rischio supera la soglia.
4. Eseguire solo dopo approvazione valida.
5. Registrare evidenza completa nel log di audit.

## Audit E Accountability

Registrare sempre:

- Chi ha richiesto l azione.
- Chi ha approvato o rifiutato.
- Motivazione della decisione.
- Input e output rilevanti.
- Timestamp UTC e versione policy applicata.

## Gestione Eccezioni Ed Escalation

- Bloccare automaticamente richieste fuori policy.
- Escalare a owner o auditor in caso di conflitto tra policy.
- Consentire override solo con motivazione formale e scadenza.
- Riesaminare periodicamente override ed eccezioni aperte.

## Deliverable

Produrre:

1. Governance model con ruoli e ownership.
2. Permission matrix.
3. Approval gates per classe di rischio.
4. Audit log schema.
5. Procedura di escalation e gestione eccezioni.

## Riferimenti

- Caricare [references/governance-template.md](references/governance-template.md) per template operativi di policy, permessi, approvazioni e audit.
