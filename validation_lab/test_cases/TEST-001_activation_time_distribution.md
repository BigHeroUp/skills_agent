# TEST-001 - Activation Time Distribution

## Metadata

- Date: 2026-06-27
- Author: Validation Lab
- Dataset: dataset operativo sintetico con sottoscrizione, creazione antenna, metodo consegna e identificativi tecnici
- Domain: telepedaggio / operations
- Priority: P1
- Status: Draft
- Related branch/commit: feature/semantic-feature-engineering

## Dataset

Schema minimo:

```csv
DATASOTTOSCRIZIONE,CREAZIONE_ANTENNA,METODOCONSEGNA,CONTRATTOID,PYID,SERIALNUMBER
2026-01-01,2026-01-03,CONSEGNA_A_MANO,C-001,PY-001,SN-001
2026-01-02,2026-01-08,POSTA,C-002,PY-002,SN-002
2026-01-03,2026-01-04,CONSEGNA_A_MANO,C-003,PY-003,SN-003
2026-01-04,2026-01-20,CONSEGNA_A_MANO,C-004,PY-004,SN-004
```

## User Prompt

Analizza la distribuzione dei tempi di attivazione usando data sottoscrizione e creazione antenna. Evidenzia percentili, outlier e giorni critici.

## Expected Result

- Expected KPIs: `TEMPO_ATTIVAZIONE_GIORNI`, record analizzati, record calcolabili, media, mediana, P75, P90, P95, P99, outlier count, negative duration count.
- Expected charts: distribuzione tempi di attivazione, eventuale trend temporale, concentrazione outlier per giorno.
- Expected insights: spiegazione semplice di media, mediana e P95; distinzione tra outlier reale e possibile problema qualita dati.
- Expected exclusions: nessuna top list su `PYID`, `CONTRATTOID`, `SERIALNUMBER` o codici tecnici.
- Expected follow-up behavior: filtro su `METODOCONSEGNA=CONSEGNA_A_MANO` rilancia analisi locale una sola volta.

## Actual Result

- Summary: Da compilare dopo esecuzione.
- Generated KPIs:
- Generated charts:
- Generated insights:
- PDF/report:
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

Questo test copre Semantic Feature Engineering, Intent Planner, Statistical Engine, Explainability / Report, Dashboard UX e LLM Gateway.

