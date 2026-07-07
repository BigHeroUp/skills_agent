# TEST-004 - Datetime Shift Activation Time

## Metadata

- Date: 2026-06-27
- Author: Validation Lab
- Dataset: dataset operativo sintetico con data sottoscrizione GMT, creazione antenna, metodo consegna e identificativi tecnici
- Domain: telepedaggio / operations
- Priority: P1
- Status: Draft
- Related branch/commit: feature/analytical-planning-engine

## Dataset

Schema minimo:

```csv
DATASOTTOSCRIZIONE,CREAZIONE_ANTENNA,METODOCONSEGNA,CANALETECNICO,PYID,CONTRATTOID
2026-01-01 10:00:00,2026-01-03 10:00:00,CONSEGNA_A_MANO,WEB,PY-001,C-001
2026-01-04 23:30:00,2026-02-13 23:30:00,DOMICILIO,BACKOFFICE,PY-002,C-002
2026-01-10 10:00:00,2026-01-09 10:00:00,CONSEGNA_A_MANO,WEB,PY-003,C-003
```

## User Prompt

Le date di data sottoscrizione sono in GMT: aggiungi +1h a data sottoscrizione e post aggiornamento analizza la distribuzione dei tempi di attivazione da data sottoscrizione a creazione antenna, capisci se i tempi lunghissimi sono riconducibili a giornate specifiche o a varianza.

## Expected Result

- Expected preprocessing: creazione di `DATASOTTOSCRIZIONE_ADJUSTED` con shift `+1h`; `DATASOTTOSCRIZIONE` originale invariata.
- Expected feature engineering: `TEMPO_ATTIVAZIONE_GIORNI` usa `DATASOTTOSCRIZIONE_ADJUSTED` come start e `CREAZIONE_ANTENNA` come end.
- Expected quality gate: durate negative rilevate come problema qualita dato; se >5% richiedono decisione utente, ma la policy sicura le esclude dai KPI principali.
- Expected KPIs: mediana, P95, outlier positivi e conteggio durate negative escluse.
- Expected charts: massimo 4 grafici pianificati, usando l'asse temporale adjusted quando serve.
- Expected follow-up behavior: una richiesta filtrata su `METODOCONSEGNA=CONSEGNA_A_MANO` produce un confronto baseline vs subset che inizia con `Confronto con analisi precedente`.
- Expected report: risposta breve prima dei dettagli; nessun dizionario grezzo, `method_details` o `row_index`.

## Actual Result

- Summary: Da compilare dopo esecuzione.
- Generated KPIs:
- Generated charts:
- Generated insights:
- Follow-up comparison:
- Logs:

## Quality Gate Evaluation

- Passed:
- Failed:
- Not applicable:

## Issues Found

| ID | Component | Priority | Description | Evidence |
|---|---|---|---|---|

## Decision

- Needs Fix / Pass / Fail

## Notes

Questo test copre Analytical Planning Engine, Semantic Feature Engineering, Data Quality Gate, Intent Planner, Follow-up Analysis, Report e Dashboard UX.
