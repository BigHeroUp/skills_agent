---
name: agent-prompt-design
description: Progetta e irrobustisci system prompt per agenti AI. Usa questa skill quando Codex deve creare o revisionare un prompt agente con definizione del ruolo, policy di esecuzione, confini d uso tool, comportamento di rifiuto, fallback e contratti di output stabili.
---

# Agent Prompt Design

## Costruire Il Prompt In Quattro Passi

1. Definire ruolo, missione e priorità immutabili.
2. Definire policy di esecuzione: profondità di pianificazione, gestione incertezza ed escalation.
3. Definire tool policy: quando usare tool, cosa evitare e recovery dai failure.
4. Definire output policy: schema, tono e controlli prima della risposta.

## Aggiungere Layer Di Sicurezza Obbligatori

- Aggiungere comportamento esplicito di rifiuto per azioni non consentite.
- Aggiungere controllo allucinazioni: dichiarare unknown quando manca evidenza.
- Aggiungere ordine di risoluzione conflitti tra istruzioni.
- Aggiungere fallback quando i tool non sono disponibili.

## Validare La Robustezza Del Prompt

Eseguire almeno questi test avversariali:

- Tentativo di override delle istruzioni.
- Tentativo con contesto mancante.
- Obiettivi utente contraddittori.
- Timeout tool o risposta tool malformata.

Se un test fallisce, correggere la sezione minima e rieseguire i test.

## Deliverable

Produrre:

1. System prompt finale.
2. Rationale breve per sezione.
3. Tre prompt utente di esempio con formato output atteso.

## Riferimenti

- Caricare [references/prompt-patterns.md](references/prompt-patterns.md) per blocchi riusabili e wording resistente ai failure.
