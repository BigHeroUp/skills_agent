# Implementation Summary - Learning Query Suggestion Agent

## Stato

Implementazione MVP completata.

Il progetto include un agente che interpreta descrizioni in linguaggio naturale,
suggerisce query o colonne per l'estrazione dati e apprende dalle query usate in
precedenza tramite uno storico SQLite locale.

## Obiettivo

Permettere a utenti non esperti di analizzare dati senza scrivere manualmente SQL
o selezionare colonne una per una.

L'utente descrive l'analisi desiderata, per esempio:

```text
Analizza i top 5 clienti per volume di ordini
```

Il sistema produce un suggerimento di estrazione dati coerente con la sorgente:

- query Oracle read-only per database Oracle;
- colonne e piano di analisi per CSV o Excel.

## File creati

### `agents/query_suggestion_agent.py`

Nuovo agente della pipeline.

Responsabilita:

- leggere la descrizione naturale dell'utente;
- identificare il tipo sorgente (`oracle`, `csv`, `excel`);
- cercare query simili nello storico;
- riusare query storiche con buona similarita;
- generare nuove query o piani tramite LLM quando non esistono match;
- salvare il suggerimento nel contesto.

### `utils/query_history_manager.py`

Gestore dello storico SQLite delle query.

Responsabilita:

- creare e inizializzare `data/query_history.db`;
- aggiungere nuove query;
- cercare query simili con `SequenceMatcher`;
- aggiornare feedback e contatori;
- restituire le query migliori per tipo sorgente.

Metodi principali:

- `add_query()`
- `find_similar_queries()`
- `update_feedback()`
- `get_top_queries()`
- `clear_history()`

### `skills/query_suggestion/SKILL.md`

Skill dedicata alla generazione di query o piani di estrazione da descrizioni
in linguaggio naturale.

### `test_integration.py`

Script di test per verificare:

- import dei moduli principali;
- integrazione del `QuerySuggestionAgent`;
- funzionamento del `QueryHistoryManager`;
- generazione di suggerimenti per sorgenti Oracle, CSV ed Excel.

### `test_new_modules.py`

Script di test focalizzato su nuovi moduli e import.

## File modificati

### `coordinator.py`

Modifiche principali:

- import di `QuerySuggestionAgent`;
- creazione delle directory richieste;
- inserimento del nuovo agente nella pipeline;
- aggiornamento del flusso a 7 agenti.

Pipeline attuale:

```text
DataSourceManager
QuerySuggestion
DataExtractor
DataValidator
DataProcessor
Analyst
ReportGenerator
```

### `app_dash.py`

Modifiche principali:

- timeline aggiornata per includere `QuerySuggestion`;
- flusso UI allineato alla pipeline a 7 agenti.

### `README.md`

Documentazione aggiornata con:

- nuova architettura;
- sezione sul `QuerySuggestionAgent`;
- note su SQLite e apprendimento;
- comandi di setup e test;
- limiti noti.

### `APPLICATION_CONTEXT.md`

Contesto applicativo aggiornato per descrivere il comportamento effettivamente
implementato dell'applicazione.

## Architettura della pipeline

```text
Input utente
    |
    v
DataSourceManager
    |
    v
QuerySuggestion
    |-- cerca query simili in data/query_history.db
    |-- se trova match, riusa la query storica
    `-- altrimenti genera un nuovo suggerimento con LLM
    |
    v
DataExtractor
    |
    v
DataValidator
    |
    v
DataProcessor
    |
    v
Analyst
    |
    v
ReportGenerator
    |
    v
Report finale e grafici
```

## Database di learning

Il database e:

```text
data/query_history.db
```

Tabella principale:

```text
query_history
|-- id
|-- description
|-- query_text
|-- source_type
|-- feedback_score
|-- execution_count
|-- success_count
|-- created_at
|-- last_used
`-- notes
```

## Flusso di apprendimento

1. L'utente descrive un'analisi.
2. Il sistema cerca richieste simili nello storico.
3. Se trova una query utile, la riusa.
4. Se non trova query simili, ne genera una nuova.
5. La nuova query viene salvata nello storico.
6. In futuro, richieste simili possono riutilizzare quella query.

Il calcolo della similarita usa `SequenceMatcher`, quindi non genera costi
OpenAI aggiuntivi.

## Sicurezza

Vincoli mantenuti:

- Oracle e read-only.
- Sono consentite solo query `SELECT` o `WITH`.
- Non sono consentite query mutative o DDL.
- Password e query Oracle non devono essere scritte nei log.
- `.env` non deve essere versionato.

## Stato delle fasi

| Fase | Task | Stato |
| --- | --- | --- |
| 1 | Creare database storico query | Completato |
| 1 | Creare skill query suggestion | Completato |
| 1 | Creare history manager | Completato |
| 2 | Creare learning agent | Completato |
| 2 | Integrare agent nel coordinator | Completato |
| 3 | Collegare feedback handler | Da fare |
| 3 | Aggiornare report generator con feedback | Da fare |
| 4 | Testare learning agent | Completato |
| 4 | Aggiornare timeline UI | Completato |

## Prossimi passi consigliati

1. Eseguire i test:

```powershell
python test_new_modules.py
python test_integration.py
```

2. Avviare la dashboard:

```powershell
python main.py
```

3. Completare il feedback loop:

- controllo UI per indicare se il suggerimento e stato utile;
- chiamata a `QueryHistoryManager.update_feedback()`;
- aggiornamento di `success_count`, `execution_count` e `feedback_score`.

4. Aggiungere le skill mancanti:

- `skills/data_validation/SKILL.md`
- `skills/data_processing/SKILL.md`
- `skills/analysis/SKILL.md`

5. Rafforzare l'analisi deterministica sui dataframe con calcoli pandas:

- KPI;
- aggregazioni;
- trend;
- anomalie;
- statistiche descrittive.

## Benefici ottenuti

- L'utente puo descrivere l'analisi in linguaggio naturale.
- Il sistema puo riusare query storiche.
- Le query ricorrenti diventano piu veloci da generare.
- Il costo LLM si riduce quando esiste uno storico utile.
- Lo storico crea una base per miglioramenti futuri tramite feedback.
