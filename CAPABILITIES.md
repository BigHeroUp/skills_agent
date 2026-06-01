# Capabilities

| Capability | Stato | File principali | Note |
| --- | --- | --- | --- |
| Dashboard Dash | Done | `app_dash.py`, `main.py` | UI locale su `http://localhost:8050/`. |
| Upload CSV | Done | `app_dash.py`, `connectors/data_connectors.py` | Lettura pandas, Dask per file grandi da filesystem. |
| Upload Excel | Done | `app_dash.py`, `connectors/data_connectors.py` | Lettura tramite pandas/openpyxl. |
| Oracle read-only | Done | `connectors/data_connectors.py`, `utils/oracle_query_validator.py` | Solo `SELECT` e `WITH`; blocco keyword mutative. |
| Pipeline agenti | Done | `coordinator.py`, `agents/*.py` | Pipeline sequenziale a 7 agenti. |
| Skill prompt loading | Done | `agents/base_agent.py`, `skills/*/SKILL.md` | Gli agenti LLM includono la propria skill nel prompt. |
| Query suggestion | Done | `agents/query_suggestion_agent.py` | Riuso storico o generazione LLM. |
| Query learning | Done | `utils/query_history_manager.py` | Storico SQLite in `data/query_history.db`. |
| Query feedback | Done | `app_dash.py`, `utils/query_history_manager.py` | Pulsanti utile/non utile dopo il report. |
| Analisi deterministica | Done | `utils/data_analysis.py` | Metriche pandas reali su dataframe. |
| Grafici Plotly | Done | `utils/chart_generator.py` | Grafici generati dal dataframe reale, inclusi grafici richiesti nella descrizione utente quando riconoscibili. |
| Report finale LLM | Done | `agents/report_generator.py` | Report testuale in italiano. |
| PDF report | Done | `utils/pdf_generator.py` | Generazione PDF locale. |
| Chat follow-up | Done | `agents/conversation_agent.py`, `utils/conversation_manager.py` | Domande successive sull'analisi. |
| Anti-secret scan | Done | `scripts/check_secrets.py` | Scanner sui file versionati. |
| Verification script | Done | `scripts/verify.ps1` | Compilazione, secret scan, pytest e import dashboard. |
| Git quality gate | Done | `.githooks/pre-commit`, `scripts/install_git_hooks.ps1` | Hook opzionale installabile con PowerShell. |
| Pytest suite | Partial | `tests/` | Copre utility, query safety, history e prompt skill. Da estendere a callback UI. |
