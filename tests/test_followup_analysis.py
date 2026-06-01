from types import SimpleNamespace

import pandas as pd

import app_dash


def test_followup_analysis_computes_average_elapsed_ticket_time():
    app_dash.current_context = SimpleNamespace(
        raw_data={
            "dataframe": pd.DataFrame({
                "Data Creazione": ["2026-01-01 08:00", "2026-01-02 10:00", "2026-01-03 09:00"],
                "Data Risoluzione": ["2026-01-01 12:00", "2026-01-03 10:00", "2026-01-03 12:00"],
            })
        }
    )

    result = app_dash._try_run_followup_analysis(
        "analizzami il tempo medio trascorso tra la data di creazione del ticket e quella di risoluzione"
    )

    assert result is not None
    assert "Tempo medio" in result["message"]
    assert "10 ore" in result["message"]
    assert result["chart"] is not None


def test_followup_analysis_ignores_unrelated_messages():
    app_dash.current_context = SimpleNamespace(raw_data={"dataframe": pd.DataFrame({"A": [1]})})

    assert app_dash._try_run_followup_analysis("fammi un riepilogo") is None


def test_followup_analysis_proceeds_from_generic_confirmation():
    app_dash.current_context = SimpleNamespace(
        raw_data={
            "dataframe": pd.DataFrame({
                "pyStatusWork": ["Open", "Resolved", "Open"],
                "pxCreateDateTime": ["2026-01-01 08:00", "2026-01-02 10:00", "2026-01-03 09:00"],
                "pyResolvedTimestamp": ["2026-01-01 12:00", "2026-01-03 10:00", None],
            })
        }
    )

    result = app_dash._try_run_followup_analysis("puoi procedere?")

    assert result is not None
    assert "Totale ticket per stato" in result["message"]
    assert "Open: 2" in result["message"]
    assert "Andamento chiusure" in result["message"]
    assert "Tempo medio" in result["message"]
