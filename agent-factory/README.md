# Agent Factory

Agent Factory e una web app locale per orchestrare un sistema multi-agente capace di capire una richiesta iniziale, fare domande di chiarimento, lavorare su file o database, produrre una soluzione finale e salvare apprendimenti per migliorare i run successivi.

Il tool nasce per gestire prompt anche molto generici: l'utente puo descrivere un obiettivo in linguaggio naturale, allegare business requirement, caricare CSV/Excel/documenti, collegare un database e chiedere analisi o estrazioni senza scrivere obbligatoriamente SQL.

## Funzionalita principali

- Intake da prompt iniziale e business requirement.
- Preset operativi: `IT Ops`, `Sec Ops`, `Rev Ops`, `Strategy`.
- Chiarimenti conversazionali prima dell'elaborazione.
- Possibilita di aggiornare il contesto con nuove richieste, query o file prima di avviare gli agenti.
- Upload e analisi di CSV ed Excel.
- Lettura di file testuali `.txt` e `.md` come requirement aggiuntivi.
- Connessione a database SQLite tramite connection string.
- Test connessione database prima dell'uso.
- Introspezione automatica di schema, tabelle, colonne e relazioni.
- Esecuzione di query SQL read-only.
- Interpretazione di richieste in linguaggio naturale su database.
- Generazione automatica di SQL per richieste semplici.
- Report finale con risultato, insight dati, SQL generata e next best action.
- Memoria persistente SQLite per job, eventi e learning.
- WebSocket e polling fallback per vedere avanzamento del flow.
- UI responsive con flow canvas stile orchestrazione n8n.

## Stack

- Backend: FastAPI
- Realtime: WebSocket
- Frontend: HTML, CSS, JavaScript vanilla
- Persistenza: SQLite
- Analisi dati: pandas/openpyxl quando disponibili
- Runtime: Python 3

## Avvio rapido

```bash
cd agent-factory/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Aprire:

```text
http://127.0.0.1:8080/
```

## Flusso utente

1. L'utente sceglie un preset operativo: `IT Ops`, `Sec Ops`, `Rev Ops` o `Strategy`.
2. Scrive il prompt iniziale e gli eventuali business requirement.
3. Seleziona la fonte dati: `CSV`, `Excel`, `Database` o `Altro`.
4. Carica file oppure verifica una connessione database.
5. Avvia il flow.
6. Il sistema genera domande di chiarimento.
7. L'utente puo rispondere alle domande oppure aggiungere nuove richieste libere.
8. L'utente puo allegare altri file o database durante il clarification loop.
9. Quando il perimetro e chiaro, l'utente clicca `Avvia elaborazione`.
10. Gli agenti lavorano in sequenza/parallelo e producono il risultato finale.
11. Il learning agent salva opportunita e next best action per i run futuri.

## Preset operativi

### IT Ops

Per richieste operative: ticketing, onboarding, automazioni, SLA e runbook.

Produce:

- piano operativo;
- owner e milestone;
- rischi di esecuzione;
- azioni per ridurre lead time e incident.

### Sec Ops

Per triage incident, sicurezza, remediation e compliance.

Produce:

- incident response plan;
- risk register;
- remediation prioritaria;
- next best action su rischio e detection.

### Rev Ops

Per analisi revenue, funnel, forecast, conversione e retention.

Produce:

- insight commerciali;
- analisi pipeline;
- performance per canale o segmento;
- backlog di azioni per crescita.

### Strategy

Per business plan, scenari economici e go-to-market.

Produce:

- business plan executive;
- assunzioni economiche;
- roadmap;
- rischi e decisioni go/no-go.

## Fonti dati

### CSV

Il sistema legge file `.csv`, identifica colonne e righe, genera preview e, se trova colonne riconoscibili, calcola insight.

Esempi di colonne supportate:

- `revenue`
- `cost`
- `channel`
- `segment`
- `customers`
- `churn_rate`
- `month`

Insight calcolabili:

- ricavi totali;
- costi totali;
- margine assoluto e percentuale;
- churn medio;
- performance per canale;
- performance per segmento;
- trend temporale;
- anomalie;
- raccomandazioni operative.

### Excel

Il sistema legge file `.xlsx` e `.xls` tramite `pandas` e `openpyxl`, poi applica la stessa logica di analisi tabellare dei CSV.

### Documenti

File `.txt` e `.md` vengono usati per arricchire i business requirement. Il testo viene inserito nel contesto del job prima della fase di chiarimento.

### Database

Quando l'utente seleziona `Database`, la UI mostra:

- campo `Stringa di connessione`;
- pulsante `Verifica connessione`;
- preview dello schema;
- area `Query SQL o richiesta human language`;
- pulsante `Esegui su DB`;
- risultato immediato.

Attualmente e supportata la connessione SQLite locale.

Esempi di connection string:

```text
sqlite:////Users/nomeutente/path/database.sqlite
sqlite:///relative/path/database.sqlite
/Users/nomeutente/path/database.db
```

Dopo la verifica, il sistema:

- legge tutte le tabelle;
- legge colonne, tipi e primary key;
- conta le righe per tabella;
- legge foreign key dichiarate;
- inferisce relazioni da colonne come `customer_id`;
- salva solo la stringa mascherata negli artifact;
- mantiene la connection string raw solo in memoria runtime.

## SQL e richieste in linguaggio naturale

Se l'utente scrive una query SQL, il sistema la esegue in modalita read-only.

Sono consentite:

- `SELECT`
- `WITH`
- `PRAGMA`

Non sono consentite query mutative.

Se l'utente scrive una richiesta in linguaggio naturale, il sistema prova a:

1. interpretare le parole chiave;
2. confrontarle con nomi tabelle e colonne;
3. usare schema e relazioni;
4. generare una query SQL read-only;
5. eseguirla;
6. mostrare risultato, SQL generata e righe di preview.

Esempio:

```text
Tirami il numero totale dei device che sono stati consegnati ai clienti.
```

Output atteso:

```text
Totale record trovati in devices: 4.
```

SQL generata:

```sql
SELECT COUNT(*) AS total FROM "devices" WHERE LOWER("status") = ?
```

## Clarification loop

Dopo l'intake il sistema non parte subito con l'elaborazione finale. Prima apre una fase di chiarimenti.

In questa fase l'utente puo:

- rispondere alle domande generate dagli agenti;
- scrivere una nuova richiesta libera;
- aggiungere una query;
- riferirsi a file gia caricati;
- allegare altri file;
- aggiornare il contesto senza avviare la pipeline.

I comandi principali sono:

- `Aggiorna contesto`: aggiorna requirement, rigenera domande e mantiene il job in attesa.
- `Avvia elaborazione`: chiude i chiarimenti e avvia gli agenti.

## Agenti

### chief-orchestrator

Coordina il flow complessivo. Avvia intake, discovery, clarification loop, pipeline parallela, soluzione, governance e learning.

Responsabilita:

- imposta lo stato del job;
- pubblica eventi;
- coordina gli agenti;
- gestisce pause e resume;
- decide quando completare il job.

### discovery-agent

Legge prompt, requirement e file caricati per sintetizzare l'obiettivo primario.

Produce:

- obiettivo principale;
- presenza di file;
- tipi input;
- indicazione se i business requirement sono presenti.

### clarification-agent

Genera domande per ridurre ambiguita prima dell'elaborazione.

Domande tipiche:

- output finale atteso;
- vincoli;
- livello di dettaglio;
- KPI;
- priorita sui file caricati;
- preferenze di grafici o dashboard.

### data-intake-agent

Analizza file e database collegati.

Per CSV/Excel:

- legge colonne e righe;
- calcola preview;
- calcola null count;
- genera statistiche;
- calcola insight business se trova colonne note.

Per database:

- mantiene gli insight DB gia prodotti dalla verifica connessione;
- evita di sovrascriverli quando non ci sono file allegati.

### analysis-agent

Crea un piano operativo/analitico.

Produce:

- step di analisi;
- workstream prioritari;
- risk log;
- indicazioni su dashboard o grafici se richiesti.

### ops-agent

Valuta le dipendenze runtime necessarie.

Se il prompt richiede grafici o dashboard, puo installare:

- `plotly`
- `matplotlib`

Se il prompt richiede query o join, puo installare:

- `duckdb`

L'installazione e limitata da allowlist in `app/dependency_manager.py`.

### solution-agent

Costruisce il report finale consolidando:

- prompt;
- requirement;
- chiarimenti;
- insight dati;
- schema DB;
- SQL generata;
- risultato query;
- next best action apprese.

Se rileva una richiesta di business plan, produce una struttura specifica di business plan.

### governance-agent

Verifica completezza e qualita del risultato.

Controlla:

- chiarimenti presenti;
- soluzione generata;
- risk log presente;
- dati o DB analizzati se forniti.

Produce:

- decisione `approved` o `needs-review`;
- dettaglio dei check.

### learning-agent

Salva apprendimenti persistenti per migliorare i run successivi.

Produce:

- opportunita di miglioramento;
- next experiments;
- next best action;
- storico su SQLite.

La memoria viene salvata in:

```text
agent-factory/backend/data/agent_memory.db
```

Questa cartella e ignorata da Git.

## Memoria persistente

Il sistema usa SQLite per salvare:

- job;
- eventi;
- artifact;
- learning entries;
- raccomandazioni.

Questo permette agli agenti di recuperare suggerimenti storici e proporre next best action basate sui run precedenti.

## UI

La UI e composta da tre aree:

- sidebar sinistra: preset, prompt, requirement, fonte dati;
- canvas centrale: flow degli agenti e stato job;
- sidebar destra: clarification loop, event stream, risultato finale e learning report.

Il flow mostra gli agenti in stati:

- `queued`;
- `active`;
- `done`.

## API principali

### Creazione job

```http
POST /api/jobs
```

Input form:

- `prompt`
- `business_requirements`
- `files`
- `db_connection_id`

### Chiarimenti finali

```http
POST /api/jobs/{job_id}/clarifications
```

### Aggiornamento conversazionale

```http
POST /api/jobs/{job_id}/clarification-turn
```

### Snapshot job

```http
GET /api/jobs/{job_id}
```

### Stream eventi

```http
WS /api/jobs/{job_id}/stream
```

### Test connessione DB

```http
POST /api/db/test
```

Body:

```json
{
  "connection_string": "sqlite:////path/database.sqlite"
}
```

### Query DB

```http
POST /api/db/query
```

Body:

```json
{
  "connection_id": "id_ritornato_dal_test",
  "request": "Tirami il numero totale dei device consegnati ai clienti"
}
```

## Struttura progetto

```text
agent-factory/
|-- README.md
`-- backend/
    |-- requirements.txt
    |-- run.sh
    `-- app/
        |-- main.py
        |-- schemas.py
        |-- state.py
        |-- intelligence.py
        |-- dependency_manager.py
        |-- agents/
        |   |-- orchestrator.py
        |   |-- discovery.py
        |   |-- clarification.py
        |   |-- data_intake.py
        |   |-- analysis.py
        |   |-- ops.py
        |   |-- solution.py
        |   |-- governance.py
        |   |-- learning.py
        |   `-- skill_registry.py
        `-- static/
            |-- index.html
            |-- styles.css
            `-- app.js
```

Le skill locali sono in:

```text
agent-skills/
```

## Note di sicurezza

- Le query DB sono read-only.
- Le query mutative non vengono eseguite.
- Le connection string raw non vengono salvate negli artifact.
- La memoria runtime delle connessioni non e persistente.
- I dati caricati e i database demo sotto `backend/data/` sono ignorati da Git.

## Stato supporto database

Supportato ora:

- SQLite locale via connection string.

Da aggiungere:

- PostgreSQL;
- MySQL/MariaDB;
- Oracle;
- gestione credenziali persistente sicura;
- query builder piu avanzato per richieste naturali complesse.
