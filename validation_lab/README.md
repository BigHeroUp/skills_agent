# Validation Lab

Il Validation Lab e lo spazio operativo dove Skills Agent viene validato contro evidenze reali e sintetiche. Non e una cartella per nuove feature: serve a raccogliere casi di test, dataset, prompt, risultati attesi, risultati ottenuti, log, report, bug e review architetturali.

## Perche esiste

Skills Agent deve evolvere in base a evidenze osservabili, non solo in base a milestone di sviluppo. Ogni regressione, dubbio o miglioramento importante deve essere collegato a un test riproducibile e a uno o piu quality gate.

## Come usarlo

1. Creare o selezionare un test case in `test_cases/`.
2. Collegare dataset, prompt e risultato atteso.
3. Eseguire l'analisi con la versione corrente del progetto.
4. Salvare risultato ottenuto, log, PDF/report e screenshot se utili.
5. Valutare i quality gate in `quality_gates.md`.
6. Se emerge un problema, creare un bug report in `bug_reports/`.
7. Considerare una fix verificata solo quando il test case passa e il bug report contiene evidenze aggiornate.

## Naming

- Test case: `TEST-XXX_short_description.md`
- Bug report: `BUG-XXX_short_description.md`
- Architecture review: `ARCH-XXX_short_description.md`
- Dataset piccoli: `DATASET-XXX_short_description.csv`
- Risultati attesi: `EXPECTED-XXX_short_description.md`

Usare lo stesso numero quando un bug o un expected result nasce da un test specifico.

## Classificazione evidenze

- Dataset: file o descrizione dello schema usato.
- Prompt: richiesta esatta dell'utente.
- Expected: KPI, grafici, esclusioni, comportamento follow-up.
- Actual: output reale generato.
- Logs: righe rilevanti, non dump completi se contengono segreti.
- Report/PDF: allegato o path del file generato.
- Screenshot: evidenza UI solo quando serve.

## Collegare bug e sottosistema

Ogni bug deve dichiarare un componente impattato:

- Data Ingestion
- Semantic Understanding
- Semantic Feature Engineering
- Intent Planner
- Statistical Engine
- Root Cause Engine
- Explainability / Report
- Dashboard UX
- LLM Gateway
- Learning Engine
- Domain Packs

## Fix verificata

Una fix e verificata quando:

- il test case originale passa;
- non introduce regressioni nei quality gate collegati;
- il bug report contiene evidenza `Actual` aggiornata;
- i comandi di verifica del progetto sono passati;
- eventuali limiti residui sono esplicitati.

## Schema minimo

```text
TEST-001
Dataset:
Prompt:
Expected:
Actual:
Status:
Impacted component:
Priority:
Evidence:
```

