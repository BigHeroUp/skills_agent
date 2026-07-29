# BUG-REV-018 - Semantica ambigua di `unique_values` con categoria nulla

## Origine

- Campagna: validazione interna single-user
- Caso: `REV-018` / `adversarial-count-null-category`
- Feedback: `partial`, rating 4, chiarezza 3, utilità 4

## Problema

Il risultato visualizzava tre categorie (`A`, `B`, `N/D`) ma riportava
`unique_values=2`, perché la cardinalità era calcolata con esclusione dei null
originari. Il calcolo dei conteggi era corretto, ma il nome del campo rendeva
ambigua l'interpretazione.

## Correzione

- `unique_values` ora indica il numero di categorie effettivamente visualizzate;
- `displayed_unique_values` rende esplicita la stessa cardinalità;
- `non_null_unique_values` conserva la cardinalità dei soli valori non nulli.

## Regressione

`tests/test_analysis_engine.py::test_count_occurrences_by_category_is_deterministic_and_json_safe`
verifica il contratto con `open`, `closed` e un valore nullo normalizzato come
`N/D`.
