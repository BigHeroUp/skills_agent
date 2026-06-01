# Working Context

## Stato corrente

Il progetto e una dashboard locale Dash per analisi dati assistita da agenti LLM.
Il branch principale e `main` ed e collegato a:

```text
https://github.com/BigHeroUp/skills_agent
```

Ultimo blocco completato:

- agenti LLM collegati ai rispettivi `SKILL.md`;
- feedback query in dashboard;
- analisi deterministica pandas;
- skill mancanti aggiunte;
- test e verifica locale introdotti.

## Vincoli permanenti

- Non versionare `.env`, password, API key o token.
- Oracle e read-only: solo `SELECT` o `WITH`.
- Separare risultati calcolati dal dataframe da testo generato dall'LLM.
- Non perdere il dataframe reale durante la pipeline.
- Aggiornare documentazione e test quando cambia il comportamento.

## Comandi di verifica

```powershell
.\scripts\verify.ps1
```

Verifiche singole:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe test_new_modules.py
.\.venv\Scripts\python.exe test_integration.py
.\.venv\Scripts\python.exe -c "import app_dash; print('OK app import')"
```

## Prossimi step

1. Estendere i test pytest sui callback Dash principali.
2. Migliorare feedback query con rating granulare e note utente.
3. Aggiungere statistiche di successo query nella dashboard.
4. Valutare un `QuerySafetyAgent` esplicativo sopra il validator deterministico.
5. Consolidare i vecchi script `test_*.py` come wrapper o rimuoverli dopo migrazione completa.
