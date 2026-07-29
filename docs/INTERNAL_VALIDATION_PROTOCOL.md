# Protocollo di validazione interna single-user

Questo protocollo permette di migliorare il prodotto mentre non sono disponibili
tester beta esterni. Le valutazioni raccolte sono evidenze interne autentiche, ma
non sostituiscono feedback indipendenti e non rendono verde il gate
`validated_accuracy` della private beta.

## Campione

Eseguire almeno 20 analisi, distribuendole tra:

- conteggi e segmentazioni;
- aggregazioni numeriche e classifiche;
- trend temporali;
- qualità dati, null e duplicati;
- richieste ambigue o non supportate.

Usare almeno tre dataset sintetici o anonimizzati. Inserire deliberatamente date
italiane e ISO, null, duplicati, valori negativi, categorie Unicode e colonne dal
nome ambiguo.

## Procedura

1. Scrivere il risultato atteso prima di eseguire l'analisi.
2. Salvare identificativo tecnico, prompt, categoria e versione del commit.
3. Confrontare calcoli e conclusioni con il risultato atteso.
4. Assegnare esito `correct`, `partial` o `incorrect` e rating 1-5.
5. Collegare ogni errore a un caso riproducibile nel Validation Lab.
6. Correggere il difetto e rieseguire sia il caso sia la regressione completa.

## Criteri interni

- almeno 20 valutazioni completate;
- almeno 90% di esiti `correct`;
- zero errori silenziosi o risultati inventati;
- 100% delle richieste non supportate con astensione o errore chiaro;
- zero bug critici aperti.

Il modello di registrazione è
`validation_lab/internal_validation_template.json` e non deve contenere dati
personali, righe sorgente, token o informazioni sensibili.

## Campagna compilabile

La campagna pronta per la revisione è generata con:

```bash
python3 scripts/build_internal_validation_campaign.py
```

Produce un DOCX con 20 schede e un JSON gemello in
`validation_lab/deliverables/`. Dopo la compilazione dei campi `[COMPILARE]`,
il feedback può essere validato e importato con:

```bash
python3 scripts/import_internal_validation_feedback.py \
  /path/to/Veraxis_Campagna_Validazione_Interna_compilata.docx \
  --campaign-json validation_lab/deliverables/Veraxis_Campagna_Validazione_Interna.json \
  --output validation_lab/internal_feedback.reviewed.json
```

Il file reviewed deve restare locale se contiene note sensibili. Gli outcome
`partial` e `incorrect` vanno collegati a test riproducibili prima di aggiornare
qualsiasi indicatore di qualità.
