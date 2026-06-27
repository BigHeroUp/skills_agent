# TEST-003 - Running Training Performance

## Metadata

- Date: 2026-06-27
- Author: Validation Lab
- Dataset: allenamenti running sintetici
- Domain: sport / training
- Priority: P2
- Status: Draft
- Related branch/commit: feature/semantic-feature-engineering

## Dataset

Schema minimo:

```csv
data,distanza_km,durata_minuti,passo_medio,frequenza_cardiaca_media
2026-01-01,5.0,31,6.2,148
2026-01-05,6.0,36,6.0,151
2026-01-12,7.0,41,5.86,153
2026-01-19,8.0,46,5.75,158
2026-01-26,6.0,42,7.0,181
```

## User Prompt

Analizza il miglioramento degli allenamenti, il carico e le anomalie nella frequenza cardiaca.

## Expected Result

- Expected KPIs: distanza totale, durata media, passo medio, trend passo, frequenza cardiaca media, outlier cardio.
- Expected charts: trend passo nel tempo, trend distanza, scatter frequenza cardiaca/passo.
- Expected insights: miglioramento o peggioramento del passo, variazione del carico, sedute anomale.
- Expected exclusions: nessuna raccomandazione medica; interpretazione solo sportiva e descrittiva.
- Expected follow-up behavior: filtro per periodo o distanza minima deve ricalcolare KPI localmente.

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

Questo test valida metriche continue, trend temporali, outlier spiegabili e limiti di dominio.

