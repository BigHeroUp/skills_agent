from types import SimpleNamespace

import pandas as pd

import app_dash


def test_followup_chart_generates_status_occurrence_bar_chart():
    app_dash.current_context = SimpleNamespace(
        raw_data={
            "dataframe": pd.DataFrame({
                "Ticket ID": [1, 2, 3, 4],
                "Stato Ticket": ["Aperto", "Chiuso", "Aperto", "In corso"],
            })
        }
    )

    result = app_dash._try_generate_followup_chart(
        "fammi un grafico a colonne con l'occorrenza dello stato ticket"
    )

    assert result is not None
    assert "Stato Ticket" in result["message"]
    assert result["figure"].data[0].y.tolist() == [2, 1, 1]


def test_followup_chart_ignores_non_chart_messages():
    app_dash.current_context = SimpleNamespace(raw_data={"dataframe": pd.DataFrame({"stato": ["A"]})})

    assert app_dash._try_generate_followup_chart("spiegami il report") is None
