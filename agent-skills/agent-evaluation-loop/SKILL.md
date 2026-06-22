---
name: agent-evaluation-loop
description: Costruisci cicli di valutazione ripetibili per agenti AI. Usa questa skill quando Codex deve definire dataset di test, rubriche di scoring, controlli regressione, gate di rilascio e iterazioni di miglioramento.
---

# Agent Evaluation Loop

## Costruire La Pipeline Di Valutazione

1. Definire famiglie di task e comportamenti attesi.
2. Costruire un test set bilanciato tra casi semplici, medi e difficili.
3. Definire metriche di scoring e soglie di pass.
4. Eseguire baseline evaluation e salvare risultati.
5. Confrontare le modifiche con la baseline e segnalare regressioni.
6. Consentire il rilascio solo con criteri espliciti superati.

## Metriche Obbligatorie

- Task success rate
- Format compliance rate
- Hallucination rate
- Policy violation rate
- Tool failure recovery rate
- P95 latency e costo per run

## Policy Regressioni

- Bloccare il rilascio se aumentano le policy violation.
- Bloccare il rilascio se la success rate scende oltre tolleranza.
- Consentire rilascio solo con eccezioni documentate e mitigazione.

## Deliverable

Produrre:

1. Test matrix.
2. Tabella scorecard.
3. Decisione di rilascio: pass, conditional pass o fail.
4. Backlog remediation ordinato per priorità.

## Riferimenti

- Caricare [references/evaluation-scorecard.md](references/evaluation-scorecard.md) per template di matrice e scoring.
