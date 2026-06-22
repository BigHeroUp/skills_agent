# Template Discovery

## Domande Di Intake

1. Quale decisione di business o azione utente deve migliorare questo agente?
2. Cosa accade oggi senza agente?
3. Qual e il piu piccolo output utile di un run riuscito?
4. Quali fonti dati sono affidabili e disponibili oggi?
5. Quali azioni sono vietate anche se migliorano il risultato?
6. Qual e il tasso di errore accettabile?
7. Qual e la latenza massima accettabile per run?
8. Quali ruoli possono revisionare o annullare l output agente?

## Matrice Vincoli

| Dimensione | Target | Limite Rigido | Note |
|---|---|---|---|
| Latenza |  |  |  |
| Costo |  |  |  |
| Accuratezza |  |  |  |
| Privacy |  |  |  |
| Sicurezza |  |  |  |

## Pattern Acceptance Test

- Happy path: input completo con output ad alta confidenza.
- Campo mancante: input parziale con fallback deterministico.
- Input ambiguo: dati in conflitto con richiesta chiarimento.
- Conflitto policy: input che richiede rifiuto o alternativa sicura.

## Checklist Handoff

- Obiettivo misurabile.
- Input/output con contratti di formato.
- Non-obiettivi espliciti.
- Tool richiesti elencati.
- Acceptance test iniziali presenti.
