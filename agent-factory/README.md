# Agent Factory (Multi-Agent System)

Sistema multi-agente con:
- chiarimenti obbligatori pre-elaborazione
- input da prompt, business requirement e file CSV/Excel
- input da prompt, business requirement testuali e file `.txt/.md/.csv/.xlsx`
- esecuzione parallela di agenti
- installazione runtime librerie (allowlist) per nuove richieste
- UI realtime responsive con diaframma animato del flusso agenti
- loop di apprendimento continuo

## Stack

- Backend: FastAPI + WebSocket
- Frontend: HTML/CSS/JS vanilla (responsive)

## Avvio rapido

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Aprire: http://127.0.0.1:8080

## Agenti implementati

- `chief-orchestrator`
- `discovery-agent`
- `clarification-agent`
- `data-intake-agent`
- `analysis-agent`
- `solution-agent`
- `governance-agent`
- `ops-agent`
- `learning-agent`

Ogni agente e collegato a una skill del pacchetto `agent-skills` tramite `app/agents/skill_registry.py`.

## Flusso

1. Intake e discovery
2. Domande chiarificatrici al cliente
3. Pipeline parallela (Data + Analysis + Ops)
4. Soluzione finale
5. Governance check
6. Learning report per miglioramento continuo

## Installazione librerie on-demand

Il sistema tenta installazioni pip automatiche solo per pacchetti in allowlist:
- `pandas`, `openpyxl`, `matplotlib`, `plotly`, `duckdb`, `numpy`, `scikit-learn`

La logica e in `app/dependency_manager.py`.
