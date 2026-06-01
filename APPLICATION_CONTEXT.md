# My Skill Agent - Contesto per AI e Agent

## Scopo del documento

Questo file descrive il comportamento effettivamente implementato dell'applicazione
`my_skill_agent`. Deve essere letto da qualsiasi AI o agent che debba comprendere,
manutenere o estendere il software.

Principio operativo: non assumere che una funzionalita dichiarata nei prompt o
nelle skill sia disponibile nell'interfaccia o autorizzata dal codice. Fare
sempre riferimento ai vincoli descritti in questo documento e ai moduli Python.

## Obiettivo dell'applicazione

L'applicazione e una dashboard locale di analisi dati assistita da LLM. Consente
all'utente di:

- caricare dati da file CSV o Excel;
- collegarsi a un database Oracle e leggere dati tramite query;
- descrivere in linguaggio naturale l'analisi desiderata;
- eseguire una pipeline sequenziale di agenti;
- visualizzare grafici Plotly generati dal dataframe reale;
- leggere un report testuale in italiano generato tramite OpenAI;
- monitorare operazioni ed errori in un file di log.

L'interfaccia web viene eseguita in locale con Dash su
`http://127.0.0.1:8050` tramite `python main.py`.

## Stack tecnico

| Ambito | Tecnologia |
| --- | --- |
| Linguaggio | Python |
| Interfaccia web | Dash |
| Grafici | Plotly |
| Elaborazione dati | pandas, Dask per CSV grandi |
| Excel | openpyxl |
| Database | oracledb |
| LLM | OpenAI Python SDK, modello configurato `gpt-3.5-turbo` |
| Configurazione | `python-dotenv`, variabile `OPENAI_API_KEY` |
| Logging | `logging` con `RotatingFileHandler` |

## File principali

| File | Responsabilita |
| --- | --- |
| `main.py` | Entry point; avvia il server Dash sulla porta 8050. |
| `app_dash.py` | Layout responsive, callback UI, upload, verifica Oracle, avvio analisi e rendering risultati. |
| `coordinator.py` | Orchestrazione sequenziale della pipeline multi-agent. |
| `utils/context.py` | Definizione del contesto condiviso `AgentContext`. |
| `utils/data_analysis.py` | Calcoli deterministici pandas sul dataframe reale. |
| `utils/chart_generator.py` | Produzione automatica di grafici Plotly dal dataframe. |
| `utils/logging_config.py` | Configurazione centralizzata del logging applicativo. |
| `connectors/data_connectors.py` | Connettori Oracle, CSV ed Excel e factory delle sorgenti. |
| `agents/*.py` | Implementazione degli agenti della pipeline. |
| `skills/*/SKILL.md` | Prompt/istruzioni disponibili per skill esplicite. |

## Flusso utente

### File CSV o Excel

1. L'utente seleziona `CSV` o `Excel`.
2. La dashboard mostra l'area per trascinare o selezionare un file.
3. Il file viene letto in memoria come `pandas.DataFrame`.
4. L'utente inserisce la descrizione dell'analisi.
5. Il dataframe viene passato alla pipeline.
6. A fine elaborazione la UI mostra report e grafici.

### Oracle Database

1. L'utente seleziona `Oracle Database`.
2. L'area upload viene nascosta.
3. La dashboard mostra i campi `Host`, `Porta`, `Service name / Database`,
   `Utente` e `Password`.
4. L'utente seleziona `Verifica connessione`.
5. Il software apre una connessione Oracle e verifica l'accesso tramite
   `SELECT 1 FROM dual`.
6. Solo dopo verifica riuscita vengono resi utilizzabili query e descrizione
   dell'analisi.
7. L'utente inserisce una query Oracle di sola lettura e la descrizione.
8. La pipeline legge i dati reali dal database, produce report e grafici.

Le credenziali Oracle rimangono in memoria nel processo server per la sessione
corrente; non devono essere scritte nei log o nei file di progetto.

## Pipeline multi-agent

Il coordinatore esegue gli agenti nell'ordine seguente:

| Ordine | Agente | Input principale | Output nel contesto |
| --- | --- | --- | --- |
| 1 | `DataSourceManagerAgent` | metadata sorgente | `raw_data` con dataframe, colonne, righe e sorgente |
| 2 | `QuerySuggestionAgent` (NUOVO) | `user_input` + `source_type` | `extraction_suggestion` con query suggerita e similarity score |
| 3 | `DataExtractorAgent` | richiesta utente e `extraction_suggestion` | `extraction_plan` prodotto dal LLM |
| 4 | `DataValidatorAgent` | `raw_data` | `validation_results`, `is_valid` |
| 5 | `DataProcessorAgent` | dati ritenuti validi | `processed_data` con `deterministic_summary` e report testuale |
| 6 | `AnalystAgent` | `processed_data` | `insights` con `deterministic_insights` e report testuale |
| 7 | `ReportGeneratorAgent` | insight e dati processati | `final_report` |

La pipeline è sequenziale: ogni agente riceve e aggiorna la medesima istanza di
`AgentContext`.

## AgentContext

Il contesto condiviso contiene:

| Campo | Contenuto |
| --- | --- |
| `user_input` | Descrizione dell'analisi richiesta. |
| `raw_data` | Dati caricati e piano di estrazione; include il dataframe reale. |
| `validation_results` | Report di validazione generato dal LLM. |
| `is_valid` | Indicatore di validita usato per consentire la lavorazione successiva. |
| `processed_data` | Report testuale e riepilogo deterministico del dataframe. |
| `insights` | Analisi LLM e insight deterministici calcolati. |
| `final_report` | Report finale mostrato nella UI. |
| `errors` | Errori accumulati durante la pipeline. |
| `metadata` | Configurazione sorgente e informazioni operative. |
| `created_at` | Timestamp di creazione del contesto. |

## Trattamento effettivo dei dati

Il dataframe reale viene acquisito da CSV, Excel o Oracle e viene usato per
generare i grafici. La pipeline mantiene tale dataframe in `raw_data`.

Il sistema calcola anche un riepilogo deterministico del dataframe reale tramite
pandas: forma del dataset, tipi dato, valori mancanti, duplicati, statistiche
numeriche, top valori categorici, correlazioni e range temporali.

Validazione e report finale restano principalmente contenuti testuali prodotti
dal modello OpenAI. Elaborazione e insight sono affiancati da risultati
deterministici salvati rispettivamente in `processed_data["deterministic_summary"]`
e `insights["deterministic_insights"]`.

## Sorgenti dati supportate

### CSV

- Upload dalla dashboard.
- Lettura tramite pandas.
- Supporto Dask nei connettori per file su filesystem oltre 100 MB.

### Excel

- Upload dalla dashboard.
- Lettura tramite pandas/openpyxl.

### Oracle

- Connessione tramite `oracledb`.
- Configurazione UI: host, porta, service/database, utente e password.
- Test connessione disponibile dalla dashboard.
- Esecuzione dati tramite `OracleConnector.query`.
- Sono consentite in esecuzione solo query che iniziano con `SELECT` o `WITH`.

## Grafici generati

`ChartGenerator.auto_generate_charts` puo produrre automaticamente:

- istogrammi per colonne numeriche;
- heatmap di correlazione;
- grafico top valori per la prima colonna categorica;
- serie temporale se e presente una colonna con `date` o `time` nel nome;
- box plot per anomalie;
- tabella con statistiche descrittive.

## Skill presenti

Sul filesystem sono presenti tre skill esplicite:

### `skills/query_suggestion/SKILL.md` (NUOVO)

Scopo: interpretare descrizioni naturali di analisi e generare query SQL o piani di estrazione ottimali.

Utilizzo attuale nel codice:

- `QuerySuggestionAgent` la dichiara come skill per generare suggerimenti da descrizioni

Funzionamento:
- Consulta la storia di query passate memorizzata in `data/query_history.db`
- Se trova query simili con buon feedback score, le suggerisce
- Altrimenti genera una nuova query con LLM
- Integrazione con `QueryHistoryManager` per apprendimento automatico

### `skills/oracle_sql/SKILL.md`

Scopo dichiarato: assistere con SQL Oracle, ottimizzazione, spiegazione query e
analisi performance.

Utilizzo attuale nel codice:

- `DataSourceManagerAgent` la dichiara come skill;
- `DataExtractorAgent` la dichiara come skill;
- `QuerySuggestionAgent` la utilizza per generare query da descrizioni Oracle

Vincolo applicativo superiore alla skill: anche se il file skill cita
`INSERT`, `UPDATE` e `DELETE`, la dashboard e il connettore dell'applicazione
consentono solo lettura (`SELECT` o `WITH`). Un agent non deve aggirare tale
vincolo.

### `skills/email_writer/SKILL.md`

Scopo dichiarato: scrivere comunicazioni professionali in italiano.

Utilizzo attuale nel codice:

- `ReportGeneratorAgent` la dichiara come skill per produrre il report finale.

### Skill data_validation, data_processing e analysis

Sono presenti anche le skill:

- `skills/data_validation/SKILL.md`
- `skills/data_processing/SKILL.md`
- `skills/analysis/SKILL.md`

Nota: nella implementazione attuale gli agenti costruiscono direttamente il
proprio prompt e non invocano `load_skill_prompt()` durante `process()`.

## OpenAI e lingua

- Ogni agente eredita da `BaseAgent`.
- Il client OpenAI richiede `OPENAI_API_KEY` nel file `.env`.
- Il modello configurato nel codice e `gpt-3.5-turbo`.
- `BaseAgent.call_openai()` aggiunge un messaggio di sistema che richiede
  risposte sempre in italiano.

## Logging e monitoraggio

Il sistema registra eventi in:

`logs/app.log`

Caratteristiche:

- rotazione automatica a 2 MB;
- conservazione di 5 archivi precedenti;
- registrazione di avvio, upload, test Oracle, connessioni, pipeline, agenti,
  chiamate OpenAI ed errori;
- esclusione intenzionale di password e contenuto delle query Oracle.

Comando PowerShell per seguire il log:

```powershell
Get-Content .\logs\app.log -Encoding UTF8 -Wait
```

## Configurazione ed esecuzione locale

Prerequisiti:

- ambiente virtuale Python;
- dipendenze da `requirements.txt`;
- `.env` contenente una chiave OpenAI valida;
- per Oracle, rete e credenziali valide verso il database.

Avvio raccomandato:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

URL della dashboard:

```text
http://localhost:8050/
```

## Sicurezza e vincoli per modifiche future

Un AI o agent che lavora su questo progetto deve rispettare queste regole:

1. Non registrare mai API key, password Oracle o altri segreti.
2. Non inserire credenziali reali in `.env.template`, README o altri file
   versionabili.
3. Non abilitare query Oracle mutative senza una decisione esplicita
   dell'utente e adeguate protezioni; il comportamento corrente e read-only.
4. Non sostituire o perdere il dataframe reale durante i passaggi della
   pipeline.
5. Conservare la dashboard responsive per desktop e dispositivi stretti.
6. Distinguere nei report e nella documentazione tra risultati calcolati dal
   dataframe e contenuti generati dall'LLM.

## Limiti noti e opportunita di evoluzione

- I risultati analitici testuali non sono ancora derivati da calcoli completi
  e verificabili sul dataframe.
- La configurazione Oracle e mantenuta in memoria server e non implementa
  isolamento multiutente.
- Lo stato della dashboard usa variabili globali di processo; non e adatto a
  esecuzioni concorrenti o deployment multi-worker.
- Mancano test automatici strutturati nel repository.
- Le skill `data_validation`, `data_processing` e `analysis` non sono ancora
  presenti come file dedicati.

Queste aree sono i principali punti di attenzione per un agent incaricato di
rendere l'applicazione piu robusta o pronta per uso condiviso.
