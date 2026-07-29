# Working Context

## Stato corrente

Il progetto e una piattaforma locale offline-first di Analytical Intelligence,
con pipeline di produzione basata sul Coordinator e Veraxis Kernel mantenuto in
parallelo finche la parita analitica non sara dimostrata su un perimetro piu
ampio.

Il branch principale e `main` ed e collegato a:

```text
https://github.com/BigHeroUp/skills_agent
```

Ultimo blocco completato:

- Milestone 23: segmentazione categoriale multidimensionale;
- Milestone 24: Kernel Analytical Parity;
- Milestone 25: Private Beta Readiness;
- benchmark beta sintetico e riproducibile su 40 casi e 10 domini, inclusi
  10 contratti avversariali;
- feedback tenant-scoped e metriche aggregate;
- probe bounded di carico e concorrenza;
- retention, cancellazione, backup e restore;
- manuale utente beta e manuale completo di prodotto.

Verifica del 29 luglio 2026:

- benchmark funzionale: 40/40 casi superati;
- readiness: 9/10 gate superati;
- unico gate non superato: accuratezza validata, per assenza dei 10 feedback
  verificati minimi;
- retention dry-run: nessun record scaduto;
- parsing data esplicito per formati ISO e italiani, senza format guessing;
- parita Kernel estesa a aggregazioni, top-N, controlli qualita e trend;
- protocollo di validazione interna single-user disponibile;
- gate pre-beta e retention dry-run automatizzati in CI;
- tooltip contestuali disponibili sulle principali funzionalita del portale.
- Milestone 26 completata con ingestion robusta, anteprima del piano, Quality
  Center, export PDF/DOCX, onboarding, hardening sicurezza e performance probe.
- performance deterministica locale verificata su 10.000, 100.000 e 1.000.000
  righe; i tempi osservati dipendono dall'hardware e non sono soglie SLA.
- validazione interna single-user importata su 20 casi: 19 corretti, 1 parziale,
  0 errati, rating medio 4,95;
- feedback `REV-018` trasformato in bug riproducibile e corretto rendendo
  esplicita la differenza tra categorie visualizzate e valori non nulli.

## Vincoli permanenti

- Non versionare `.env`, password, API key, token o artefatti beta sensibili.
- Oracle e read-only: solo `SELECT` o `WITH`.
- Separare risultati calcolati dal dataframe da testo generato dall'LLM.
- Non perdere il dataframe reale durante la pipeline.
- Aggiornare documentazione e test quando cambia il comportamento.
- Non dichiarare pronta la private beta senza evidenze verificabili.
- Il Coordinator resta il production boundary finche la parita Kernel non e
  dimostrata su un perimetro piu ampio.

## Comandi di verifica

```bash
python3 -m pytest -q
python3 scripts/run_beta_functional_benchmark.py \
  --output /tmp/veraxis-functional-benchmark.json
python3 scripts/check_beta_readiness.py \
  validation_lab/beta_evidence.current.json
python3 scripts/enforce_retention.py --days 90
```

## Prossimi step

1. Raccogliere almeno 10 feedback verificati da utenti beta autenticati.
2. Calcolare l'accuratezza validata e raggiungere la soglia minima dell'80%.
3. Aggiornare l'artefatto locale delle evidenze senza dati personali o
   sensibili e rieseguire `check_beta_readiness.py`.
4. Correggere i casi classificati `partial` o `incorrect`, collegandoli a casi
   riproducibili nel Validation Lab, e rieseguire la regressione.
5. Autorizzare l'apertura della private beta soltanto quando tutti i gate sono
   verdi e i bug critici aperti sono zero.
