# Quality Gates

I quality gate sono criteri di accettazione osservabili. Un test case puo passare anche se alcuni gate sono non applicabili, ma ogni gate fallito deve generare una nota o un bug report.

## A. Data Ingestion

- File caricato correttamente.
- Righe e colonne coerenti con il dataset sorgente.
- Date parsate correttamente.
- Null gestiti in modo esplicito.
- Nessuna perdita silenziosa di dati.

## B. Semantic Understanding

- ID riconosciuti come ID.
- Date riconosciute come `DATE` o `DATETIME`.
- Metriche riconosciute come metriche.
- Categorie informative riconosciute.
- Colonne quasi costanti escluse da analisi poco informative.

## C. Semantic Feature Engineering

- Feature derivate create quando richieste.
- Esempio: `start_date` / `end_date` -> `duration`.
- Dataframe arricchito conserva tutte le righe originali.
- Warning per valori non parsabili o durate negative.

## D. Intent Planner

- Metrica primaria corretta.
- Time axis corretto.
- Segmentazioni utili.
- Colonne vietate escluse.
- Nessun `top PYID`, ID, serial o codici tecnici.

## E. Statistical Engine

- Statistiche coerenti con il tipo dato.
- Percentili calcolati su metriche corrette.
- Nessuna media su identificativi.
- Outlier detection spiegabile.
- Test statistici coerenti con le assunzioni richieste.

## F. Root Cause Engine

- Ipotesi supportate da evidenze.
- Alternative presenti.
- Nessuna ipotesi creativa senza dati.
- Vincoli di dominio rispettati.

## G. Explainability / Report

- Executive summary leggibile.
- KPI in formato tabellare o card.
- Massimo 5 raccomandazioni.
- Nessun dump Python o dizionario raw.
- Report leggibile da un business user in 3 minuti.

## H. Dashboard UX

- Nessuno scroll reset.
- Nessun flicker o lampeggio.
- Grafici insight-first.
- Download PDF corretto.
- Follow-up eseguito una sola volta.

## I. LLM Gateway

- OpenAI opzionale.
- Numero massimo di chiamate rispettato.
- Cache funzionante.
- GPT-5.5 senza `temperature`.
- Fallback locale non blocca la pipeline.

## J. Learning Engine

- Feedback salvato.
- Pattern versionati.
- Confidence aggiornata.
- Nessun catastrophic forgetting.

## K. Domain Packs

- Versione dichiarata.
- Mapping colonne/KPI chiaro.
- Constraint set presente.
- Backward compatibility.

## L. Privacy e Lifecycle

- Nessuna riga sorgente persistita nella richiesta.
- Feedback isolato per tenant.
- Cancellazione autorizzata e verificata.
- Retention in dry-run per default.
- Backup e restore provati in ambiente isolato.

## M. Beta Operations

- Metriche aggregate prive di dati personali.
- Probe di concorrenza bounded su payload sintetici.
- Richieste non supportate gestite esplicitamente.
- Zero bug critici aperti.
- Readiness calcolata da evidenze complete.
