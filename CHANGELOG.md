# Changelog

## Unreleased

### Added

- workflow tenant-scoped per classificare, verificare o escludere feedback beta;
- motivi diagnostici, risultato atteso, versione analizzata e riferimento a bug/test;
- modalità beta guidata con dataset sintetici e domande precompilate;
- funnel beta aggregato su accesso, piano, analisi, risultato e feedback;
- API amministrative per coda feedback, revisione e funnel aggregato.

### Changed

- il gate di accuratezza usa soltanto feedback esterni verificati e richiede
  almeno tre tester distinti;
- la modifica di un feedback già revisionato lo riporta automaticamente in
  stato `pending`;
- lo schema di piattaforma passa alla versione 5; i feedback storici migrano
  come `unclassified` e non vengono conteggiati nel gate.

## 0.26.0-rc1 - 2026-07-29

### Added

- seconda campagna avversariale con 20 contratti bounded;
- storico tenant-scoped del Quality Center;
- rate limiting distribuito Redis con fallback locale;
- anteprima analitica, export PDF/DOCX e Quality Center;
- campagna human-review da 20 casi e importazione feedback.

### Fixed

- semantica delle categorie visualizzate quando i null diventano `N/D`;
- packaging Docker dei moduli necessari al Quality Center.

### Validation

- 20 feedback interni: 19 corretti, 1 parziale successivamente corretto;
- private beta ancora `not_ready` in assenza di feedback indipendenti.
