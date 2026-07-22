# Private Beta Readiness

La private beta è autorizzabile solo tramite evidenze, non tramite una dichiarazione manuale.
Il Coordinator resta il production boundary; le capability Kernel operano esclusivamente in
modalità parallela finché la parità non è dimostrata su un perimetro più ampio.

## Gate obbligatori

| Gate | Soglia minima |
|---|---:|
| Casi riproducibili | 30 |
| Domini distinti | 3 |
| Feedback verificati | 10 |
| Accuratezza validata | 80% |
| Concorrenza probe | 5 |
| Error rate probe | massimo 2% |
| Isolamento tenant | superato |
| Richieste non supportate | astensione o errore chiaro |
| Backup e restore | prova superata |
| Retention e cancellazione | prova superata |
| Bug critici aperti | 0 |

Il file `validation_lab/beta_evidence.example.json` è intenzionalmente rosso: deve essere
copiato in un artefatto locale non versionato e compilato con evidenze reali o sintetiche
approvate. Non inserire dati sorgente, prompt sensibili, token o identificativi personali.

```bash
python3 scripts/check_beta_readiness.py /path/to/beta_evidence.json
```

Il campione funzionale incluso è sintetico e riproducibile: 30 contratti di analisi
coprono sei domini e cinque intenti per dominio. Ogni risultato viene confrontato con un
contratto atteso scritto indipendentemente dall'output del motore:

```bash
python3 scripts/run_beta_functional_benchmark.py \
  --output /tmp/veraxis-functional-benchmark.json
```

Il benchmark verifica inferenza dell'intento e calcolo deterministico. Non viene contato
come feedback utente: il gate di accuratezza resta separato per impedire auto-certificazioni.

## Feedback e metriche

Ogni utente autenticato può valutare una propria analisi con rating 1–5, esito
`correct`, `partial` o `incorrect` e una nota limitata a 1.000 caratteri. Il record è
tenant-scoped e aggiornabile dallo stesso utente. `/metrics` espone soltanto aggregati:
volumi per stato, numero feedback, rating medio ed esiti, senza tenant, email o note.

## Carico e concorrenza

Il probe usa esclusivamente un payload sintetico e limiti bounded. Il token non va passato
sulla command line. Una richiesta conta come successo soltanto quando il job raggiunge
`completed` con un risultato valido; errori di submission, job falliti e timeout rientrano
tutti nell'error rate:

```bash
export VERAXIS_BETA_TOKEN='...'
python3 scripts/beta_load_probe.py --payload /path/to/synthetic.json --requests 20 --concurrency 5
```

In ambienti locali isolati il probe può leggere una risposta temporanea di login con
`--auth-json`; il file deve restare fuori dal repository ed essere eliminato dopo il test.
`--completion-timeout` consente di adeguare l'attesa alla capacità dell'ambiente senza
alterare la soglia di qualità.

Il risultato del probe dimostra soltanto il gate tecnico e non sostituisce il campione
funzionale o i feedback degli utenti beta.

## Retention e cancellazione

La piattaforma non persiste le righe originali nella richiesta di analisi. Un amministratore
può cancellare una singola analisi tramite `DELETE /api/v1/analyses/{id}`. La retention è
dry-run per default e considera soltanto job terminali:

```bash
python3 scripts/enforce_retention.py --days 90
python3 scripts/enforce_retention.py --days 90 --apply
```

La cancellazione elimina anche i feedback associati. Knowledge Graph, Experience, log e
backup hanno lifecycle separati e devono essere inclusi nella policy dell'organizzazione.

## Backup e restore

SQLite:

```bash
python3 scripts/backup_platform.py --output-dir backups
python3 scripts/restore_platform.py backups/platform-YYYYMMDD.db --confirm
```

PostgreSQL usa `pg_dump` e `pg_restore`. La prova di restore deve avvenire su un ambiente
isolato e deve verificare schema, tenant, analisi, feedback e readiness endpoint.

## Gestione incidenti beta

1. sospendere nuovi invii se isolamento, integrità o cancellazione falliscono;
2. conservare solo log sanitizzati e identificativi tecnici minimi;
3. creare un bug riproducibile nel Validation Lab;
4. correggere e rieseguire gate mirati e regressione completa;
5. riaprire la beta soltanto con zero bug critici.
