# Changelog

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
