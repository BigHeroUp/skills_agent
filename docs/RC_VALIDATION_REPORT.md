# Rapporto di validazione 0.26.0-rc1

Data: 29 luglio 2026

## Esito

La release candidate supera i controlli automatizzabili e i collaudi reali
disponibili nell'ambiente locale. La private beta esterna resta separatamente
bloccata fino alla raccolta di feedback indipendenti.

## Evidenze

- regressione: 409 test superati;
- campagna avversariale V2: 20/20 casi superati;
- Docker E2E: gateway, API, PostgreSQL, Redis/RQ e worker superati;
- E2E: 1,597 secondi, soglia massima 30 secondi;
- isolamento tenant: superato;
- performance deterministica: 100.000 righe in 0,0069 secondi, picco 2,03 MB;
- security probe: 6/6 controlli superati;
- PDF multipagina: 3/3 pagine ispezionate, senza tagli o sovrapposizioni;
- DOCX: struttura, sezioni, titoli, contenuti, formato Letter e margini validati;
- accessibilità UI: lingua, viewport, tooltip tastiera/puntatore, nomi accessibili,
  live region e grafo SVG verificati strutturalmente.

## Limiti del collaudo

Il browser integrato e LibreOffice non erano disponibili nella sessione. Il
collaudo UI visuale e il rendering DOCX dovranno quindi essere ripetuti in un
ambiente che li esponga. Questo limite non viene convertito in un esito positivo.

## Gate residuo

Servono almeno 10 feedback verificati provenienti da utenti beta indipendenti,
accuratezza validata almeno all'80% e zero bug critici aperti prima di autorizzare
la private beta.

## Ricollaudo del 2 agosto 2026

- regressione completa: 409/409 test superati;
- benchmark funzionale: 40/40 casi superati;
- campagna avversariale V2: 20/20 casi superati;
- Docker E2E: superato in 1,578 secondi, inclusi RQ, risultato deterministico,
  Product Intelligence e isolamento tenant;
- backup e restore PostgreSQL: schema e conteggi delle sei tabelle applicative
  identici nell'ambiente temporaneo isolato;
- security probe: 6/6 controlli superati;
- performance: 100.000 righe in 0,007 secondi, picco 2,03 MB;
- DOCX: collaudo visuale manuale completato in Pages senza tagli,
  sovrapposizioni o anomalie di impaginazione;
- DOCX: 41 righe di intestazione tabella marcate semanticamente e audit di
  accessibilita concluso con zero rilievi ad alta, media o bassa severita;
- UI: collaudo visuale manuale del portale locale completato senza anomalie di
  layout, leggibilita o adattamento della finestra.

Il browser controllabile da Codex e LibreOffice non erano disponibili. Per
questo ricollaudo, le verifiche visuali UI e DOCX sono state eseguite
manualmente dall'operatore rispettivamente nel browser locale e in Pages. Il
gate dei feedback beta indipendenti resta invariato.
