import pandas as pd

from utils.chart_generator import ChartGenerator


def test_generates_requested_status_count_and_ticket_trend_charts():
    df = pd.DataFrame({
        "Ticket": [1, 2, 3, 4],
        "Stato Ticket": ["Aperto", "Chiuso", "Aperto", "In lavorazione"],
        "Data Lavorazione": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-03"],
    })

    charts = ChartGenerator.generate_requested_charts(
        df,
        "fammi un grafico a colonne con le occorrenze degli stati per tutta la lista. "
        "In piu fammi un secondo grafico con l'andamento della lavorazione dei ticket",
    )

    assert len(charts) == 2
    assert "Occorrenze per Stato Ticket" in charts[0].layout.title.text
    assert charts[0].data[0].y.tolist() == [2, 1, 1]
    assert "Andamento lavorazione ticket" in charts[1].layout.title.text


def test_requested_charts_returns_empty_for_unrecognized_request():
    df = pd.DataFrame({"Categoria": ["A", "B"], "Valore": [1, 2]})

    assert ChartGenerator.generate_requested_charts(df, "spiegami il dataset") == []
