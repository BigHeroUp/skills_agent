# Benchmark Suite

La benchmark suite definisce domini non lavorativi per validare Skills Agent senza dipendere da dati aziendali. Ogni dominio deve coprire ingestion, comprensione semantica, planning, statistiche, report e UX quando applicabile.

## Finance personale

- Tipo dataset: transazioni con data, categoria, importo, conto, metodo pagamento.
- Domande: spese mensili, categorie anomale, trend risparmio.
- KPI attesi: totale spese, media mensile, top categorie, outlier importi.
- Grafici attesi: trend mensile, barre per categoria, boxplot importi.
- Errori da intercettare: importi negativi interpretati male, categorie quasi costanti, date non parsate.

## Sport/allenamenti

- Tipo dataset: sessioni con data, distanza, durata, passo, frequenza cardiaca.
- Domande: miglioramento performance, carico settimanale, anomalie cardio.
- KPI attesi: passo medio, distanza totale, durata media, carico.
- Grafici attesi: trend passo, trend distanza, scatter cardio/passo.
- Errori da intercettare: media su ID sessione, outlier non spiegati, unita incoerenti.

## Energia domestica

- Tipo dataset: consumi giornalieri o orari per kWh, costo, fascia oraria, stanza.
- Domande: picchi consumo, costo mensile, confronto fasce.
- KPI attesi: consumo totale, costo totale, picco, media giornaliera.
- Grafici attesi: serie temporale, barre per fascia, heatmap oraria se disponibile.
- Errori da intercettare: fasce quasi costanti, timestamp non ordinati, picchi non motivati.

## Retail generico

- Tipo dataset: vendite con data, prodotto, categoria, quantita, prezzo, store.
- Domande: categorie top, anomalie vendite, stagionalita.
- KPI attesi: ricavi, quantita, ticket medio, top prodotti.
- Grafici attesi: trend vendite, barre categoria, distribuzione ticket.
- Errori da intercettare: codici prodotto trattati come metriche, resi negativi non gestiti.

## Meteo

- Tipo dataset: osservazioni con data, temperatura, umidita, pioggia, vento.
- Domande: trend temperatura, giorni estremi, correlazioni meteo.
- KPI attesi: media temperatura, massimi/minimi, giorni pioggia.
- Grafici attesi: linee temperatura, barre pioggia, scatter umidita/temperatura.
- Errori da intercettare: unita miste, null su sensori, outlier fisicamente impossibili.

## Log applicativi

- Tipo dataset: timestamp, servizio, livello, latency, status code, endpoint.
- Domande: errori per servizio, degrado latency, endpoint critici.
- KPI attesi: error rate, P95 latency, count errori, top endpoint.
- Grafici attesi: trend errori, percentile latency, barre per servizio.
- Errori da intercettare: status code trattato come metrica continua, ID richiesta usati nei top.

## Sanita sintetica

- Tipo dataset: visite simulate con data, reparto, durata attesa, esito, priorita.
- Domande: tempi attesa, reparti critici, anomalie durata.
- KPI attesi: attesa media/mediana/P95, volumi reparto, outlier.
- Grafici attesi: boxplot attese, trend giornaliero, barre reparto.
- Errori da intercettare: raccomandazioni cliniche non supportate, dati sensibili reali, causalita inventata.

## Universita/esami

- Tipo dataset: esami con studente anonimizzato, corso, voto, data, CFU.
- Domande: andamento voti, corsi critici, distribuzione CFU.
- KPI attesi: voto medio, mediana, pass rate, CFU totali.
- Grafici attesi: istogramma voti, trend pass rate, barre corso.
- Errori da intercettare: ID studente come metrica, campioni piccoli non segnalati.

## Cinema/recensioni

- Tipo dataset: film, genere, data, rating, durata, piattaforma.
- Domande: generi migliori, trend rating, anomalie durata/rating.
- KPI attesi: rating medio, count recensioni, top generi.
- Grafici attesi: barre genere, distribuzione rating, trend temporale.
- Errori da intercettare: rating fuori scala, genere quasi costante, duplicati film.

## Formula 1

- Tipo dataset: gare, pilota, team, posizione, tempo giro, pit stop.
- Domande: performance piloti, anomalie pit, trend team.
- KPI attesi: posizione media, best lap, pit time medio, punti.
- Grafici attesi: trend posizioni, boxplot pit, barre punti.
- Errori da intercettare: numero pilota come metrica, circuiti ad alta cardinalita non contestualizzati.

## Calcio

- Tipo dataset: partite, squadra, gol, xG, possesso, tiri, data.
- Domande: rendimento squadre, anomalie xG/gol, trend forma.
- KPI attesi: punti, gol fatti/subiti, xG medio, conversion rate.
- Grafici attesi: trend punti, scatter xG/gol, barre squadre.
- Errori da intercettare: partite duplicate, home/away ignorato, classifiche su ID.

## IoT/sensori

- Tipo dataset: timestamp, device, metrica, valore, location, stato.
- Domande: anomalie sensori, drift, downtime.
- KPI attesi: uptime, P95 valore, outlier count, device critici.
- Grafici attesi: serie temporale, heatmap device, distribuzione valori.
- Errori da intercettare: device ID come metrica, timestamp mancanti, valori impossibili non segnalati.

