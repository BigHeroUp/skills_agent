"""Service applicativi usati dalla dashboard Dash.

Questo modulo contiene lo stato runtime e le analisi deterministiche usate
anche dai test esistenti, senza dipendere da componenti Dash.
"""

import base64
import io
import json
import threading
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import plotly.express as px

from agents.analyst import AnalystAgent
from agents.data_processor import DataProcessorAgent
from agents.report_generator import ReportGeneratorAgent
from coordinator import Coordinator
from services.analytical_planning_engine import FollowupComparisonPlanner
from services.analytical_intent_planner import AnalyticalIntentPlanner
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from utils.context import AgentContext
from utils.pdf_generator import PDFGenerator


def default_processing_status():
    return {"status": "idle", "current_agent": "", "progress": 0}


def default_query_feedback_status():
    return {"query_id": None, "submitted": False, "message": ""}


@dataclass
class DashboardRuntimeState:
    """Stato runtime condiviso dalle callback Dash.

    Dash invoca callback stateless, ma questa applicazione usa elaborazioni
    asincrone in background. Lo stato viene centralizzato qui per evitare
    variabili globali sparse in app_dash.py.
    """

    coordinator: Any = None
    current_context: Any = None
    processing_status: dict = field(default_factory=default_processing_status)
    uploaded_df: Any = None
    oracle_connection_config: dict | None = None
    query_feedback_status: dict = field(default_factory=default_query_feedback_status)
    conversation_manager: Any = None
    conversation_agent: Any = None
    pdf_generator: PDFGenerator = field(default_factory=PDFGenerator)
    current_charts: list = field(default_factory=list)
    followup_charts: list = field(default_factory=list)
    results_rendered: bool = False
    cached_results_view: dict = field(default_factory=dict)
    followup_lock: Any = field(default_factory=threading.Lock)
    followup_processing: bool = False
    last_followup_request_id: str | None = None
    last_processed_n_clicks: int = 0

    def reset_for_analysis(self):
        """Resetta solo lo stato volatile di una nuova elaborazione."""
        self.current_context = None
        self.processing_status = {"status": "starting", "current_agent": "", "progress": 0}
        self.current_charts = []
        self.followup_charts = []
        self.results_rendered = False
        self.cached_results_view = {}
        self.followup_processing = False
        self.last_followup_request_id = None
        self.last_processed_n_clicks = 0


def parse_uploaded_dataframe(contents: str, filename: str, source_type: str):
    """Decodifica un upload CSV/Excel e ritorna dataframe e metadata invariati."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    if source_type == 'csv':
        dataframe = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    elif source_type == 'excel':
        dataframe = pd.read_excel(io.BytesIO(decoded))
    else:
        raise ValueError("Il caricamento file è disponibile solo per CSV o Excel.")

    metadata = {
        "source_type": source_type,
        "file_path": filename,
        "file_size_mb": len(decoded) / (1024 * 1024)
    }
    return dataframe, metadata


def run_analysis_pipeline(
    description: str,
    context_metadata: str | None,
    source_type: str,
    uploaded_df,
    oracle_connection_config: dict | None,
    oracle_query: str | None,
    progress_callback,
):
    """Prepara metadata e invoca la pipeline multi-agent esistente."""
    if source_type == 'oracle':
        metadata = {
            "source_type": "oracle",
            "oracle_config": oracle_connection_config.copy(),
            "oracle_query": oracle_query.strip(),
        }
    else:
        metadata = json.loads(context_metadata)
        metadata["source_type"] = source_type

        if uploaded_df is not None:
            metadata["dataframe"] = uploaded_df

    coordinator = Coordinator()
    return coordinator.run(
        description,
        metadata=metadata,
        progress_callback=progress_callback,
    )


def try_generate_followup_chart(user_message: str, current_context):
    """Genera grafici deterministici richiesti in chat quando possibile."""
    if current_context is None:
        return None

    message = user_message.lower()
    wants_chart = any(term in message for term in ["grafico", "chart", "colonne", "barre", "bar chart"])
    wants_status = any(term in message for term in ["stato", "status", "state"])
    wants_occurrence = any(term in message for term in ["occorrenza", "conteggio", "quanti", "totale", "somma"])
    if not (wants_chart and (wants_status or wants_occurrence)):
        return None

    df = current_context.raw_data.get("dataframe")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    status_col = find_status_column(df)
    if not status_col:
        available = ", ".join(map(str, df.columns[:15]))
        return {
            "figure": px.bar(title="Colonna stato non trovata"),
            "description": "Colonna stato/status non individuata.",
            "message": (
                "Non ho trovato una colonna riconducibile allo stato del ticket. "
                f"Colonne disponibili: {available}"
            ),
        }

    counts = (
        df[status_col]
        .fillna("N/D")
        .astype(str)
        .value_counts(dropna=False)
        .reset_index()
    )
    counts.columns = [str(status_col), "Occorrenze"]

    show_all = any(term in message for term in ["tutti", "tutte", "completo", "intera lista"])
    suffix = ""
    if not show_all and len(counts) > 50:
        counts = counts.head(50)
        suffix = " (prime 50 categorie)"

    fig = px.bar(
        counts,
        x=str(status_col),
        y="Occorrenze",
        title=f"Occorrenze per {status_col}{suffix}",
        labels={str(status_col): str(status_col), "Occorrenze": "Occorrenze"},
        text="Occorrenze",
    )
    fig.update_layout(template="plotly_dark", height=460, xaxis_tickangle=-35)
    fig.update_traces(textposition="outside")

    return {
        "figure": fig,
        "description": f"Grafico generato dalla chat: conteggio occorrenze per '{status_col}'.",
        "message": f"Ho generato un grafico a colonne con le occorrenze per '{status_col}' usando tutti i ticket disponibili nel dataframe.",
    }


def find_status_column(df: pd.DataFrame):
    """Trova la colonna piu probabile per stato/status ticket."""
    keywords = ["stato", "status", "state", "ticket status", "ticket state"]
    normalized_columns = [(column, str(column).lower().replace("_", " ")) for column in df.columns]

    for column, normalized in normalized_columns:
        if any(keyword in normalized for keyword in keywords):
            return column

    categorical = [
        column for column in df.columns
        if pd.api.types.is_object_dtype(df[column])
        or pd.api.types.is_string_dtype(df[column])
        or isinstance(df[column].dtype, pd.CategoricalDtype)
    ]
    low_cardinality = [
        column for column in categorical
        if 1 < df[column].nunique(dropna=True) <= 30
    ]
    return low_cardinality[0] if low_cardinality else None


def try_run_knowledge_graph_query(user_message: str) -> dict | None:
    """Esegue una query deterministica sul Knowledge Graph quando richiesta."""
    message = (user_message or "").strip()
    if not _looks_like_knowledge_graph_query(message):
        return None

    try:
        result = KnowledgeGraphQueryEngine().answer_question_deterministic(message)
    except Exception as exc:
        result = {
            "question": message,
            "answer": f"Knowledge Graph non disponibile: {exc}",
            "matches": [],
            "confidence": 0.0,
            "execution_type": "deterministic_kg_query",
        }
    result["message"] = format_knowledge_graph_chat_response(result)
    return result


def _looks_like_knowledge_graph_query(user_message: str) -> bool:
    message = (user_message or "").lower()
    keywords = [
        "knowledge graph",
        "grafo",
        "grafo conoscenza",
        "codice",
        "funzioni",
        "funzione",
        "classi",
        "classe",
        "file",
        "import",
        "anomalie",
        "anomalia",
        "root cause",
        "cause radice",
        "colonne",
        "colonna",
        "report",
        "analisi precedenti",
    ]
    return any(keyword in message for keyword in keywords)


def format_knowledge_graph_chat_response(result: dict[str, Any]) -> str:
    """Formatta una risposta KG compatta e leggibile nella chat Dash."""
    answer = result.get("answer") or "Nessuna risposta disponibile dal Knowledge Graph."
    confidence = result.get("confidence", 0.0)
    lines = [
        answer,
        f"Confidence: {confidence:.2f}" if isinstance(confidence, (int, float)) else f"Confidence: {confidence}",
        f"Execution type: {result.get('execution_type', 'deterministic_kg_query')}",
    ]

    matches = result.get("matches") or []
    if matches:
        lines.append("Primi match:")
        for index, match in enumerate(matches[:10], start=1):
            node_type = match.get("type", "node")
            label = match.get("label") or match.get("id", "")
            properties = _format_match_properties(match.get("properties") or {})
            suffix = f" | {properties}" if properties else ""
            lines.append(f"{index}. [{node_type}] {label}{suffix}")
    return "\n".join(lines)


def _format_match_properties(properties: dict[str, Any]) -> str:
    if not isinstance(properties, dict) or not properties:
        return ""
    parts = []
    for key, value in list(properties.items())[:5]:
        if isinstance(value, (dict, list, tuple, set)):
            rendered = f"{type(value).__name__}({len(value)})"
        else:
            rendered = str(value)
        if len(rendered) > 80:
            rendered = rendered[:77] + "..."
        parts.append(f"{key}={rendered}")
    return ", ".join(parts)


def try_run_followup_analysis(user_message: str, current_context):
    """Esegue analisi deterministiche richieste dalla chat quando possibile."""
    if current_context is None:
        return None

    filtered = try_run_filtered_reanalysis(user_message, current_context)
    if filtered:
        return filtered

    message = user_message.lower()
    wants_ticket_overview = any(term in message for term in [
        "puoi procedere", "procedi", "fammi tutto", "fai tutto", "quanto hai detto",
        "quello che hai detto", "andamento chiusura", "andamento delle chiusura",
        "chiusura ticket", "chiusure ticket", "numero totali degli stati",
        "totali degli stati", "stati per tutta la lista",
    ])
    if wants_ticket_overview:
        result = run_ticket_overview_analysis(current_context)
        if result:
            return result

    wants_elapsed_time = (
        any(term in message for term in ["tempo medio", "durata media", "tempo trascorso", "tempo di risoluzione"])
        and any(term in message for term in ["creazione", "apertura", "created", "creation"])
        and any(term in message for term in ["risoluzione", "aggiornamento", "chiusura", "resolved", "updated", "closed"])
    )
    if not wants_elapsed_time:
        return None

    df = current_context.raw_data.get("dataframe")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "message": "Non posso calcolare il tempo medio: non trovo un dataframe disponibile nell'analisi corrente.",
            "description": "Analisi tempo medio non eseguita.",
        }

    start_col = find_datetime_column_by_keywords(df, [
        "creazione", "apertura", "created", "creation", "open", "opened", "start", "data creazione",
    ])
    end_col = find_datetime_column_by_keywords(df, [
        "risoluzione", "aggiornamento", "chiusura", "resolved", "updated", "closed", "close", "end",
        "data risoluzione", "data aggiornamento",
    ])

    if not start_col or not end_col or start_col == end_col:
        available = ", ".join(map(str, df.columns[:20]))
        return {
            "message": (
                "Non posso calcolare il tempo medio: non ho individuato una coppia chiara di colonne data "
                f"per creazione e risoluzione/aggiornamento. Colonne disponibili: {available}"
            ),
            "description": "Analisi tempo medio non eseguita.",
        }

    start_dates = pd.to_datetime(df[start_col], errors="coerce")
    end_dates = pd.to_datetime(df[end_col], errors="coerce")
    durations = end_dates - start_dates
    valid_durations = durations[(start_dates.notna()) & (end_dates.notna()) & (durations >= pd.Timedelta(0))]

    if valid_durations.empty:
        return {
            "message": (
                f"Ho trovato le colonne '{start_col}' e '{end_col}', ma non ci sono durate valide "
                "con entrambe le date presenti e fine successiva alla creazione."
            ),
            "description": "Analisi tempo medio non eseguita.",
        }

    total_rows = len(df)
    valid_rows = len(valid_durations)
    invalid_rows = total_rows - valid_rows
    average = valid_durations.mean()
    median = valid_durations.median()
    minimum = valid_durations.min()
    maximum = valid_durations.max()

    chart_df = pd.DataFrame({"Durata ore": valid_durations.dt.total_seconds() / 3600})
    fig = px.histogram(
        chart_df,
        x="Durata ore",
        nbins=30,
        title=f"Distribuzione durata ticket: {start_col} -> {end_col}",
        labels={"Durata ore": "Durata in ore"},
    )
    fig.update_layout(template="plotly_dark", height=440)

    message_text = (
        f"Ho calcolato il tempo tra '{start_col}' e '{end_col}' su {valid_rows} ticket validi "
        f"su {total_rows} righe totali.\n\n"
        f"- Tempo medio: {format_timedelta_it(average)}\n"
        f"- Mediana: {format_timedelta_it(median)}\n"
        f"- Minimo: {format_timedelta_it(minimum)}\n"
        f"- Massimo: {format_timedelta_it(maximum)}\n"
        f"- Righe escluse per date mancanti/non valide: {invalid_rows}\n\n"
        "Ho aggiunto anche un grafico di distribuzione della durata nella sezione grafici."
    )

    return {
        "message": message_text,
        "chart": fig,
        "description": f"Distribuzione della durata ticket calcolata tra '{start_col}' e '{end_col}'.",
    }


def try_run_filtered_reanalysis(user_message: str, current_context):
    """Rilancia la pipeline analitica locale su un dataframe filtrato da follow-up."""
    df = current_context.raw_data.get("dataframe") if current_context else None
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    planner = AnalyticalIntentPlanner()
    filter_spec = planner.parse_followup_filter(user_message, df)
    if not filter_spec:
        return None

    filtered_df = planner.apply_followup_filter(df, filter_spec)
    if filtered_df.empty:
        return {
            "message": (
                f"Ho riconosciuto il filtro {filter_spec['column']} == {filter_spec['value']}, "
                "ma non ci sono record corrispondenti nel dataframe corrente."
            ),
            "description": "Ri-analisi filtrata non eseguita: subset vuoto.",
            "applied_filters": [filter_spec],
            "filtered_row_count": 0,
            "followup_execution_type": "filtered_reanalysis",
        }

    original_request = getattr(current_context, "user_input", "")
    reanalysis_request = (
        f"{original_request}\n\nFollow-up filtrato: {user_message}. "
        f"Analizza solo i record con {filter_spec['column']} == {filter_spec['value']}."
    )
    metadata = dict(getattr(current_context, "metadata", {}) or {})
    metadata["source_type"] = metadata.get("source_type") if metadata.get("source_type") in {"csv", "excel"} else "csv"
    context = AgentContext(
        user_input=reanalysis_request,
        raw_data={
            "dataframe": filtered_df.copy(),
            "row_count": len(filtered_df),
            "columns": list(filtered_df.columns),
            "source": "followup_filtered_reanalysis",
            "shape": filtered_df.shape,
        },
        metadata=metadata,
    )
    context.followup_execution_type = "filtered_reanalysis"
    context.applied_filters = [filter_spec]
    context.filtered_row_count = int(len(filtered_df))

    for agent in (DataProcessorAgent(), AnalystAgent(), ReportGeneratorAgent()):
        context = agent.process(context)

    context.followup_execution_type = "filtered_reanalysis"
    context.applied_filters = [filter_spec]
    context.filtered_row_count = int(len(filtered_df))
    context.processed_data["followup_execution_type"] = context.followup_execution_type
    context.processed_data["applied_filters"] = context.applied_filters
    context.processed_data["filtered_row_count"] = context.filtered_row_count

    comparison = FollowupComparisonPlanner().compare(
        df,
        context.raw_data.get("dataframe"),
        filter_spec,
        "TEMPO_ATTIVAZIONE_GIORNI",
    )
    context.followup_comparison_results = comparison
    context.processed_data["followup_comparison_results"] = comparison

    comparison_message = format_followup_comparison_message(comparison)

    return {
        "message": (
            f"Confronto con analisi precedente\n\n"
            f"{comparison_message}\n\n"
            f"Ho rilanciato l'analisi sul subset filtrato: "
            f"{filter_spec['column']} == {filter_spec['value']}.\n\n"
            f"- Righe filtrate: {len(filtered_df)} su {len(df)}\n"
            f"- Tipo esecuzione: filtered_reanalysis\n\n"
            f"{context.final_report}"
        ),
        "description": f"Ri-analisi filtrata su {filter_spec['column']} == {filter_spec['value']}.",
        "context": context,
        "applied_filters": [filter_spec],
        "filtered_row_count": int(len(filtered_df)),
        "followup_execution_type": "filtered_reanalysis",
    }


def format_followup_comparison_message(comparison: dict[str, Any]) -> str:
    baseline = comparison.get("baseline") or {}
    subset = comparison.get("subset") or {}
    delta = comparison.get("delta") or {}
    return "\n".join([
        f"- Filtro: {comparison.get('filter', 'n/a')}",
        f"- Righe baseline: {comparison.get('baseline_rows', 0)}",
        f"- Righe subset: {comparison.get('subset_rows', 0)}",
        (
            f"- Mediana baseline/subset: {format_number_it(baseline.get('median'))} / "
            f"{format_number_it(subset.get('median'))} giorni"
        ),
        (
            f"- P95 baseline/subset: {format_number_it(baseline.get('p95'))} / "
            f"{format_number_it(subset.get('p95'))} giorni"
        ),
        (
            f"- Delta P95: {format_number_it(delta.get('p95_pct'))}%"
        ),
        (
            f"- Delta quota outlier positivi: "
            f"{format_number_it(delta.get('outlier_ratio_delta'))}"
        ),
    ])


def run_ticket_overview_analysis(current_context):
    """Calcola analisi ticket principali dal dataframe corrente."""
    df = current_context.raw_data.get("dataframe") if current_context else None
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "message": "Non posso procedere: non trovo il dataframe dell'analisi corrente.",
            "description": "Analisi ticket non eseguita.",
        }

    messages = [f"Ho analizzato il dataframe corrente: {len(df)} righe e {len(df.columns)} colonne."]
    chart = None
    description = "Analisi ticket deterministica."

    status_col = find_status_column(df)
    if status_col:
        counts = df[status_col].fillna("N/D").astype(str).value_counts(dropna=False)
        messages.append(f"\nTotale ticket per stato usando la colonna '{status_col}':")
        for status, count in counts.items():
            messages.append(f"- {status}: {int(count)}")

        counts_df = counts.reset_index()
        counts_df.columns = [str(status_col), "Occorrenze"]
        chart = px.bar(
            counts_df,
            x=str(status_col),
            y="Occorrenze",
            title=f"Occorrenze per {status_col}",
            labels={str(status_col): str(status_col), "Occorrenze": "Occorrenze"},
            text="Occorrenze",
        )
        chart.update_layout(template="plotly_dark", height=460, xaxis_tickangle=-35)
        chart.update_traces(textposition="outside")
        description = f"Totale ticket per stato calcolato su '{status_col}'."
    else:
        messages.append("\nNon ho individuato una colonna stato/status per il conteggio per stato.")

    closure_col = find_datetime_column_by_keywords(df, [
        "risoluzione", "chiusura", "resolved", "closed", "close", "data risoluzione", "data chiusura",
        "pyresolvedtimestamp",
    ])
    if closure_col:
        closure_dates = pd.to_datetime(df[closure_col], errors="coerce")
        valid_closures = closure_dates.dropna()
        if not valid_closures.empty:
            span_days = max((valid_closures.max() - valid_closures.min()).days, 0)
            freq = "ME" if span_days > 730 else "W" if span_days > 120 else "D"
            trend = valid_closures.to_frame(name="data").set_index("data").resample(freq).size()
            messages.append(f"\nAndamento chiusure usando la colonna '{closure_col}':")
            messages.append(f"- Chiusure con data valida: {int(valid_closures.count())}")
            messages.append(f"- Prima chiusura: {valid_closures.min().date()}")
            messages.append(f"- Ultima chiusura: {valid_closures.max().date()}")
            if not trend.empty:
                peak_date = trend.idxmax()
                messages.append(f"- Periodo con piu chiusure: {peak_date.date()} ({int(trend.max())} ticket)")
        else:
            messages.append(f"\nLa colonna '{closure_col}' non contiene date di chiusura valide.")
    else:
        messages.append("\nNon ho individuato una colonna data di chiusura/risoluzione per l'andamento nel tempo.")

    elapsed = calculate_elapsed_time_summary(df)
    if elapsed:
        messages.append("\nTempo tra creazione e risoluzione/aggiornamento:")
        messages.extend(elapsed)

    return {
        "message": "\n".join(messages),
        "chart": chart,
        "description": description,
    }


def calculate_elapsed_time_summary(df: pd.DataFrame):
    start_col = find_datetime_column_by_keywords(df, [
        "creazione", "apertura", "created", "creation", "open", "opened", "start", "data creazione",
        "pxcreatedatetime",
    ])
    end_col = find_datetime_column_by_keywords(df, [
        "risoluzione", "aggiornamento", "chiusura", "resolved", "updated", "closed", "close", "end",
        "data risoluzione", "data aggiornamento", "pyresolvedtimestamp", "pyupdatedatetime", "pxupdatedatetime",
    ])
    if not start_col or not end_col or start_col == end_col:
        return []

    start_dates = pd.to_datetime(df[start_col], errors="coerce")
    end_dates = pd.to_datetime(df[end_col], errors="coerce")
    durations = end_dates - start_dates
    valid_durations = durations[(start_dates.notna()) & (end_dates.notna()) & (durations >= pd.Timedelta(0))]
    if valid_durations.empty:
        return []

    return [
        f"- Colonne usate: '{start_col}' -> '{end_col}'",
        f"- Ticket validi: {len(valid_durations)} su {len(df)}",
        f"- Tempo medio: {format_timedelta_it(valid_durations.mean())}",
        f"- Mediana: {format_timedelta_it(valid_durations.median())}",
        f"- Minimo: {format_timedelta_it(valid_durations.min())}",
        f"- Massimo: {format_timedelta_it(valid_durations.max())}",
    ]


def find_datetime_column_by_keywords(df: pd.DataFrame, keywords):
    """Trova una colonna data coerente con una lista di keyword."""
    candidates = [
        column for column in df.columns
        if any(keyword in str(column).lower().replace("_", " ") for keyword in keywords)
    ]
    for column in candidates:
        parsed = pd.to_datetime(df[column], errors="coerce")
        if parsed.notna().sum() >= max(2, int(len(df) * 0.2)):
            return column
    return None


def format_timedelta_it(delta: pd.Timedelta) -> str:
    """Formatta una durata pandas in italiano leggibile."""
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} giorni")
    if hours:
        parts.append(f"{hours} ore")
    if minutes or not parts:
        parts.append(f"{minutes} minuti")
    return ", ".join(parts)


def format_number_it(value: Any) -> str:
    """Formatta valori numerici opzionali per messaggi business leggibili."""
    if value is None:
        return "n/a"
    try:
        if pd.isna(value):
            return "n/a"
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)
