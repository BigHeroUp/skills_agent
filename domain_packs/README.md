# Domain Intelligence Packs

I domain pack contengono conoscenza di dominio caricabile localmente senza
modificare il core engine.

Ogni pack deve vivere in una directory dedicata e includere questi file:

- `domain_pack.yaml`: manifest del pack.
- `patterns.json`: pattern analitici di dominio.
- `kpi_definitions.json`: KPI e metriche attese.
- `strategy_rules.json`: regole strategiche locali.
- `questions.json`: domande di chiarimento.
- `terminology.json`: concetti, sinonimi e segnali lessicali.
- `report_template.md`: traccia report orientata al dominio.

I pack devono essere JSON-safe e funzionare senza chiamate OpenAI.
