"""Entry point Dash per la dashboard multi-agent.

Il modulo mantiene gli oggetti pubblici storici (`app` e helper `_...`) per
compatibilita con `main.py` e con i test esistenti.
"""

import dash

from services.analysis_service import (
    DashboardRuntimeState,
    calculate_elapsed_time_summary,
    find_datetime_column_by_keywords,
    find_status_column,
    format_timedelta_it,
    run_ticket_overview_analysis,
    try_generate_followup_chart,
    try_run_followup_analysis,
)
from ui.callbacks import register_callbacks
from ui.layout import DASH_INDEX_STRING, create_layout
from utils.logging_config import get_logger


app = dash.Dash(__name__)
app.title = "Multi-Agent Data Analysis Platform"
logger = get_logger("dashboard")
runtime_state = DashboardRuntimeState()

app.index_string = DASH_INDEX_STRING
app.layout = create_layout(runtime_state.processing_status)
register_callbacks(app, runtime_state, logger)


@app.server.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# Compatibilita con test e script che importano queste variabili da app_dash.
current_context = None


def _try_generate_followup_chart(user_message: str):
    return try_generate_followup_chart(user_message, current_context)


def _try_run_followup_analysis(user_message: str):
    return try_run_followup_analysis(user_message, current_context)


def _find_status_column(df):
    return find_status_column(df)


def _run_ticket_overview_analysis():
    return run_ticket_overview_analysis(current_context)


def _calculate_elapsed_time_summary(df):
    return calculate_elapsed_time_summary(df)


def _find_datetime_column_by_keywords(df, keywords):
    return find_datetime_column_by_keywords(df, keywords)


def _format_timedelta_it(delta):
    return format_timedelta_it(delta)


if __name__ == '__main__':
    app.run(debug=True, port=8050)
