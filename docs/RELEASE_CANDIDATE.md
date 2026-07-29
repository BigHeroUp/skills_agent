# Veraxis 0.26.0-rc1

## Criteri di promozione

- regressione completa verde;
- campagne funzionale e avversariale verdi;
- stack Docker con PostgreSQL, Redis/RQ, API e Nginx healthy;
- registrazione, login, analisi asincrona, risultato ed export verificati;
- zero bug critici aperti;
- backup e restore provati in ambiente isolato.

## Criteri di stop

- isolamento tenant non superato;
- perdita o invenzione di risultati deterministici;
- job completato senza dati elaborati;
- API non healthy o error rate superiore al 2% nel probe bounded;
- impossibilità di cancellare dati o ripristinare un backup.

## Ambito

Questa release candidate qualifica il prodotto per collaudi controllati. Non
autorizza automaticamente la private beta: il gate dei feedback indipendenti
resta separato.
