# TEST-002 - Personal Finance Monthly Spending

## Metadata

- Date: 2026-06-27
- Author: Validation Lab
- Dataset: finanza personale sintetica
- Domain: personal finance
- Priority: P2
- Status: Draft
- Related branch/commit: feature/semantic-feature-engineering

## Dataset

Schema minimo:

```csv
data,categoria,importo,metodo_pagamento
2026-01-03,spesa,54.20,carta
2026-01-10,trasporti,18.00,bancomat
2026-01-18,ristoranti,82.50,carta
2026-02-04,spesa,61.10,carta
2026-02-12,bollette,210.00,bonifico
2026-02-19,ristoranti,95.00,carta
```

## User Prompt

Analizza le spese mensili e identifica categorie anomale o importi fuori scala.

## Expected Result

- Expected KPIs: spesa totale, media mensile, mediana transazione, top categorie, outlier importi.
- Expected charts: trend mensile spesa, barre per categoria, distribuzione importi.
- Expected insights: categorie che pesano di piu, mesi con spesa anomala, spiegazione degli importi estremi.
- Expected exclusions: nessuna media su metodo pagamento; nessuna inferenza finanziaria non supportata.
- Expected follow-up behavior: filtro per categoria o mese deve ricalcolare KPI localmente.

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

Questo test usa un dominio non lavorativo per validare statistiche descrittive, trend temporale, outlier e report business-first.

