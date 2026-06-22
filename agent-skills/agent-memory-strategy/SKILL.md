---
name: agent-memory-strategy
description: Progetta l architettura di memoria per agenti AI con memoria breve, memoria lunga, retrieval, retention e cancellazione. Usa questa skill quando Codex deve definire cosa ricordare, quando salvare, come recuperare in sicurezza e come fare pruning preservando performance e privacy.
---

# Agent Memory Strategy

## Costruire Il Modello Di Memoria

1. Separare memoria di sessione breve da memoria persistente lunga.
2. Definire unita di memoria: fatti, preferenze, decisioni e task aperti.
3. Definire trigger di scrittura e condizioni di esclusione.
4. Definire trigger di retrieval e strategia di ranking.
5. Definire policy di retention e cancellazione per classe.

## Classi Di Memoria

- `ephemeral_context`: valida solo nel run corrente.
- `session_context`: valida nella conversazione corrente.
- `persistent_fact`: riusabile tra sessioni.
- `user_preference`: riusabile ma sovrascrivibile.
- `sensitive_data`: storage ristretto con TTL severo.

## Policy Di Storage

- Salvare solo informazioni che cambiano decisioni future.
- Non salvare rumore transitorio o boilerplate ripetuto.
- Richiedere provenance per ogni memoria salvata.
- Allegare confidence e timestamp di ultima verifica.

## Policy Di Retrieval

- Recuperare per intent, recency e confidence score.
- Limitare i record richiamati a top-k per evitare context bloat.
- Risolvere conflitti preferendo memoria recente verificata.
- Con confidence bassa, chiedere conferma invece di assumere.

## Privacy E Governance

- Minimizzare la retention di dati personali o sensibili.
- Applicare TTL e workflow di cancellazione per classe.
- Supportare richieste utente di erase.
- Mantenere audit field su chi/quando/perche della scrittura o cancellazione.

## Deliverable

Produrre:

1. Memory taxonomy.
2. Regole di write e read.
3. Policy di retention e pruning.
4. Controlli privacy e cancellazione.
5. Verifiche di qualita della memoria.

## Riferimenti

- Caricare [references/memory-policy-template.md](references/memory-policy-template.md) per schema, formula ranking, pruning schedule e checklist compliance.
