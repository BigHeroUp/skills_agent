# Scorecard Valutazione

## Template Test Matrix

| Case ID | Famiglia | Difficolta | Sintesi Input | Comportamento Atteso | Pass/Fail | Note |
|---|---|---|---|---|---|---|

## Tabella Scoring

| Metrica | Baseline | Candidato | Delta | Soglia | Gate |
|---|---|---|---|---|---|
| Success rate |  |  |  | >=  |  |
| Format compliance |  |  |  | >=  |  |
| Hallucination rate |  |  |  | <=  |  |
| Policy violation rate |  |  |  | <=  |  |
| Recovery rate |  |  |  | >=  |  |
| P95 latency |  |  |  | <=  |  |
| Cost per run |  |  |  | <=  |  |

## Bucket Di Triage Failure

- Difetto prompt
- Difetto contratto tool
- Dato o contesto mancante
- Gap policy di sicurezza
- Comportamento non deterministico

## Regola Decisione Rilascio

- Pass: tutti i gate verdi.
- Conditional pass: nessun gate rosso, con accettazione rischio documentata.
- Fail: almeno un gate rosso.
