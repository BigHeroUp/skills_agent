"""Callback Dash della dashboard multi-agent."""

import json
import threading
import uuid

import pandas as pd
from dash import Input, Output, State, ctx, dcc, html, no_update

from agents.conversation_agent import ConversationAgent
from services.analysis_service import (
    parse_uploaded_dataframe,
    run_analysis_pipeline,
    try_generate_followup_chart,
    try_run_followup_analysis,
)
from services.business_insight_generator import BusinessInsightGenerator
from services.oracle_service import verify_oracle_connection
from utils.chart_generator import ChartGenerator
from utils.conversation_manager import ConversationManager
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.query_history_manager import QueryHistoryManager


def should_disable_polling(status: str) -> bool:
    """Il polling serve solo durante l'elaborazione."""
    return status not in {'processing', 'starting'}


def build_followup_request_id(n_clicks: int | None, user_message: str | None) -> str:
    """Identifica in modo stabile una richiesta follow-up da click e testo."""
    return f"{int(n_clicks or 0)}:{(user_message or '').strip()}"


def should_process_followup_request(
    n_clicks: int | None,
    user_message: str | None,
    last_processed_n_clicks: int | None,
    last_followup_request_id: str | None,
) -> bool:
    """Evita doppie esecuzioni dello stesso submit follow-up."""
    if not n_clicks or not user_message or not user_message.strip():
        return False
    request_id = build_followup_request_id(n_clicks, user_message)
    return int(n_clicks) > int(last_processed_n_clicks or 0) and request_id != last_followup_request_id


def register_callbacks(app, state, logger):
    """Registra tutte le callback Dash sull'applicazione passata."""
    @app.callback(
        Output('file-upload-container', 'style'),
        Output('oracle-config-container', 'style'),
        Output('analysis-container', 'style'),
        Output('oracle-query-container', 'style'),
        Output('start-button', 'disabled'),
        Input('source-type', 'value'),
        Input('oracle-connection-store', 'data'),
        Input('oracle-query', 'value')
    )
    def update_source_layout(source_type, oracle_state, oracle_query):
        """Mostra solo i controlli pertinenti alla fonte selezionata."""
        if source_type != 'oracle':
            return (
                {"display": "block"},
                {"display": "none"},
                {"marginTop": "20px", "display": "block"},
                {"display": "none"},
                False,
            )
    
        verified = bool(oracle_state and oracle_state.get("verified"))
        analysis_style = {"marginTop": "20px", "display": "block" if verified else "none"}
        return (
            {"display": "none"},
            {"display": "block"},
            analysis_style,
            {"display": "block"},
            not (verified and oracle_query and oracle_query.strip()),
        )
    
    
    @app.callback(
        Output('oracle-connection-status', 'children'),
        Output('oracle-connection-store', 'data'),
        Input('test-oracle-button', 'n_clicks'),
        Input('oracle-host', 'value'),
        Input('oracle-port', 'value'),
        Input('oracle-database', 'value'),
        Input('oracle-user', 'value'),
        Input('oracle-password', 'value'),
        prevent_initial_call=True
    )
    def test_oracle_connection(n_clicks, host, port, database, user, password):
        """Verifica la connessione senza inviare la password al browser store."""
    
        if ctx.triggered_id != 'test-oracle-button':
            state.oracle_connection_config = None
            logger.info("Configurazione Oracle modificata: verifica connessione invalidata")
            return html.Span(
                "Verifica nuovamente la connessione dopo aver modificato i parametri.",
                style={"color": "#ffbf69"}
            ), {"verified": False}
    
        required_values = [host, port, database, user, password]
        if not all(required_values):
            state.oracle_connection_config = None
            logger.warning("Test Oracle non avviato: parametri incompleti")
            return html.Span(
                "Compila tutti i parametri Oracle prima della verifica.",
                style={"color": "#ff6b6b"}
            ), {"verified": False}
    
        try:
            state.oracle_connection_config = verify_oracle_connection(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                logger=logger,
            )
            return html.Span(
                "Connessione Oracle verificata. Puoi configurare l'analisi.",
                style={"color": "#52d273"}
            ), {"verified": True}
        except Exception as e:
            state.oracle_connection_config = None
            logger.error("Test Oracle fallito: %s", type(e).__name__)
            return html.Span(
                f"Connessione non riuscita: {str(e)}",
                style={"color": "#ff6b6b"}
            ), {"verified": False}
    
    
    # Callback per upload
    @app.callback(
        Output('upload-status', 'children'),
        Output('context-store', 'data'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('source-type', 'value')
    )
    def update_upload(contents, filename, source_type):
        if contents is None:
            return "", None
        
        try:
            
            state.uploaded_df, metadata = parse_uploaded_dataframe(contents, filename, source_type)
    
            logger.info(
                "File caricato. source_type=%s nome=%s righe=%s colonne=%s dimensione_mb=%.2f",
                source_type,
                filename,
                len(state.uploaded_df),
                len(state.uploaded_df.columns),
                metadata["file_size_mb"],
            )
            
            status = html.Div([
                html.Span("✅ File caricato: ", style={"color": "#2ca02c"}),
                html.Span(f"{filename} ({len(state.uploaded_df)} righe, {len(state.uploaded_df.columns)} colonne)")
            ])
            
            return status, json.dumps(metadata)
        
        except Exception as e:
            logger.error("Caricamento file fallito. source_type=%s errore=%s", source_type, type(e).__name__)
            return html.Div([html.Span(f"❌ Errore: {str(e)}", style={"color": "#d62728"})]), None
    
    
    # Callback per avvio analisi
    @app.callback(
        Output('timeline-container', 'style'),
        Output('processing-store', 'data'),
        Input('start-button', 'n_clicks'),
        State('analysis-description', 'value'),
        State('context-store', 'data'),
        State('source-type', 'value'),
        State('oracle-connection-store', 'data'),
        State('oracle-query', 'value'),
        prevent_initial_call=True
    )
    def start_analysis(n_clicks, description, context_metadata, source_type, oracle_state, oracle_query):
    
        if not description:
            logger.warning("Analisi non avviata: descrizione mancante")
            return {"display": "none"}, state.processing_status
    
        if source_type == 'oracle':
            if not oracle_state.get("verified") or not state.oracle_connection_config or not oracle_query:
                logger.warning("Analisi Oracle non avviata: connessione o query non verificate")
                return {"display": "none"}, state.processing_status
        elif not context_metadata:
            logger.warning("Analisi non avviata: nessun file caricato. source_type=%s", source_type)
            return {"display": "none"}, state.processing_status
    
        state.processing_status = {
            "status": "processing",
            "current_agent": "DataSourceManager",
            "progress": 0,
        }
        state.results_rendered = False
        state.cached_results_view = {}
        state.current_charts = []
        state.query_feedback_status = {"query_id": None, "submitted": False, "message": ""}
        state.followup_charts = []
        state.followup_processing = False
        state.last_followup_request_id = None
        state.last_processed_n_clicks = 0
        logger.info("Analisi richiesta dalla dashboard. source_type=%s", source_type)
        
        def run_pipeline():
            
            try:
                def update_progress(agent_name, progress):
                    state.processing_status["current_agent"] = agent_name
                    state.processing_status["progress"] = progress
    
                state.current_context = run_analysis_pipeline(
                    description=description,
                    context_metadata=context_metadata,
                    source_type=source_type,
                    uploaded_df=state.uploaded_df,
                    oracle_connection_config=state.oracle_connection_config,
                    oracle_query=oracle_query,
                    progress_callback=update_progress,
                )
                
                state.processing_status["status"] = "completed"
                state.processing_status["current_agent"] = "Completato"
                state.processing_status["progress"] = 100
                logger.info("Analisi dashboard completata. source_type=%s", source_type)
                
            except Exception as e:
                state.processing_status["status"] = "error"
                state.processing_status["error"] = str(e)
                logger.error("Analisi dashboard fallita. source_type=%s errore=%s", source_type, type(e).__name__)
        
        # Esegui in thread parallelo
        thread = threading.Thread(target=run_pipeline)
        thread.daemon = True
        thread.start()
        
        return {"display": "block"}, state.processing_status.copy()

    @app.callback(
        Output('interval-component', 'disabled'),
        Input('processing-store', 'data'),
        Input('interval-component', 'n_intervals')
    )
    def control_polling(processing_data, n):
        """Abilita il polling solo mentre una pipeline è in corso."""
        status = state.processing_status.get('status', 'idle')
        return should_disable_polling(status)
    
    
    # Callback per update timeline
    @app.callback(
        Output('agent-timeline', 'children'),
        Output('progress-container', 'style'),
        Output('progress-fill', 'style'),
        Input('interval-component', 'n_intervals')
    )
    def update_timeline(n):
        agents = [
            "DataSourceManager",
            "QuerySuggestion",
            "DataExtractor",
            "DataValidator",
            "DataProcessor",
            "Analyst",
            "ReportGenerator"
        ]
        
        status = state.processing_status.get('status', 'idle')
        current_agent = state.processing_status.get('current_agent', '')
        progress = int(state.processing_status.get('progress', 0) or 0)
        
        if status == 'idle':
            return no_update, {"display": "none"}, {"width": "0%"}
        
        timeline = []
        current_index = agents.index(current_agent) if current_agent in agents else -1
        for i, agent in enumerate(agents):
            if status == 'error' and (agent == current_agent or (current_index < 0 and i == 0)):
                badge_class = "error"
                icon = "!"
                status_text = "Errore"
            elif agent == current_agent and status == 'processing':
                badge_class = "active"
                icon = "●"
                status_text = "In elaborazione"
            elif status == 'completed' or (status == 'processing' and current_index >= 0 and i < current_index):
                badge_class = "completed"
                icon = "✓"
                status_text = "Completato"
            else:
                badge_class = "pending"
                icon = "○"
                status_text = "In attesa"
            
            step_class = "agent-step"
            if badge_class == 'active':
                step_class += " active"
            elif badge_class == 'completed':
                step_class += " completed"
            elif badge_class == 'error':
                step_class += " error"
            
            timeline.append(
                html.Div([
                    html.Div(icon, className="agent-icon"),
                    html.Div(agent, className="agent-name"),
                    html.Div(status_text, className=f"status-badge {badge_class}")
                ], className=step_class)
            )
        
        progress_style = {"display": "block"} if status == 'processing' else {"display": "none"}
        progress_fill_style = {"width": f"{max(0, min(progress, 100))}%"}
        timeline_key = (status, current_agent)
        if getattr(update_timeline, "_last_timeline_key", None) == timeline_key:
            timeline = no_update
        else:
            update_timeline._last_timeline_key = timeline_key
        
        return timeline, progress_style, progress_fill_style
    
    
    # Callback per mostrare risultati
    @app.callback(
        Output('final-report', 'children'),
        Output('report-container', 'style'),
        Output('charts-container', 'children'),
        Output('results-container', 'style'),
        Input('interval-component', 'n_intervals')
    )
    def display_results(n):
        if state.processing_status.get('status') != 'completed' or state.current_context is None:
            return no_update, no_update, no_update, no_update
        if state.results_rendered and state.cached_results_view:
            return no_update, no_update, no_update, no_update
        
        try:
            # Mostra il report
            report_text = state.current_context.final_report if state.current_context.final_report else "Analisi completata"
            
            # Genera grafici se ci sono dati
            charts_html = []
            result_df = state.current_context.raw_data.get("dataframe")
            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                chart_generator = ChartGenerator()
                requested_charts = chart_generator.generate_requested_charts(result_df, state.current_context.user_input)
                chart_payload = chart_generator.generate_dashboard_charts(result_df, state.current_context.insights)
                automatic_charts = chart_payload["charts"]
                skipped_insights = BusinessInsightGenerator().generate_chart_exclusion_insights(
                    chart_payload.get("skipped_charts", [])
                )
                useful_note = BusinessInsightGenerator().useful_columns_insight(chart_payload)
                if useful_note:
                    skipped_insights.insert(0, useful_note)
                if skipped_insights:
                    report_text = (
                        f"{report_text}\n\n## Dashboard Insights\n"
                        + "\n".join(f"- {item}" for item in skipped_insights)
                    )
                charts = requested_charts + automatic_charts
                state.current_charts = charts
                
                for chart in charts:
                    charts_html.append(
                        html.Div([dcc.Graph(figure=chart)], className="chart-card")
                    )
    
            for item in state.followup_charts:
                charts_html.append(
                    html.Div([
                        dcc.Graph(figure=item["figure"]),
                        html.Div(item["description"], style={"color": "#aaa", "marginTop": "8px"})
                    ], className="chart-card")
                )
            
            result = {
                "report_text": report_text,
                "report_style": {"display": "block"},
                "charts_html": charts_html,
                "results_style": {"display": "block" if charts_html else "none"},
            }
            state.cached_results_view = result
            state.results_rendered = True
            return (
                result["report_text"],
                result["report_style"],
                result["charts_html"],
                result["results_style"],
            )
        
        except Exception as e:
            logger.error("Visualizzazione risultati fallita: %s", type(e).__name__)
            return f"❌ Errore nella visualizzazione: {str(e)}", {"display": "block"}, [], {"display": "none"}
    
    
    @app.callback(
        Output('query-feedback-container', 'style'),
        Output('query-feedback-status', 'children'),
        Input('interval-component', 'n_intervals'),
        Input('feedback-useful-button', 'n_clicks'),
        Input('feedback-not-useful-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_query_feedback(n_intervals, useful_clicks, not_useful_clicks):
        """Registra feedback manuale sul suggerimento query usato dall'analisi."""
    
        if state.processing_status.get('status') != 'completed' or state.current_context is None:
            return {"display": "none"}, ""
    
        suggestion = state.current_context.raw_data.get("extraction_suggestion", {})
        query_id = suggestion.get("query_id")
        analysis_pattern_id = getattr(state.current_context, "analysis_pattern_id", None)
        if not query_id and not analysis_pattern_id:
            return {"display": "none"}, html.Span(
                "Feedback non disponibile: non ci sono query o pattern analitici storicizzabili.",
                style={"color": "#aaa"}
            )
    
        feedback_key = f"query:{query_id}|analysis:{analysis_pattern_id}"
        if state.query_feedback_status.get("feedback_key") != feedback_key:
            state.query_feedback_status = {
                "feedback_key": feedback_key,
                "query_id": query_id,
                "analysis_pattern_id": analysis_pattern_id,
                "submitted": False,
                "message": "",
            }
    
        triggered = ctx.triggered_id
        if triggered in {"feedback-useful-button", "feedback-not-useful-button"}:
            if state.query_feedback_status.get("submitted"):
                return {"display": "block"}, html.Span(
                    state.query_feedback_status.get("message", "Feedback gia registrato."),
                    style={"color": "#2ca02c"}
                )
    
            success = triggered == "feedback-useful-button"
            feedback_score = 1.0 if success else 0.15
            updated_targets = []
            if query_id:
                manager = QueryHistoryManager()
                manager.update_feedback(query_id=query_id, success=success, feedback_score=feedback_score)
                updated_targets.append("query")
                logger.info("Feedback query registrato. query_id=%s success=%s", query_id, success)

            if analysis_pattern_id:
                analysis_manager = AnalysisHistoryManager()
                updated_pattern = analysis_manager.update_feedback(
                    pattern_id=analysis_pattern_id,
                    success=success,
                    feedback_score=feedback_score,
                )
                if updated_pattern:
                    state.current_context.confidence_score = updated_pattern.get("confidence_score", 0.0)
                    state.current_context.execution_summary["confidence_score"] = state.current_context.confidence_score
                    state.current_context.processed_data["confidence_score"] = state.current_context.confidence_score
                updated_targets.append("pattern analitico")
                logger.info(
                    "Feedback pattern analitico registrato. pattern_id=%s success=%s",
                    analysis_pattern_id,
                    success,
                )
    
            state.query_feedback_status = {
                "feedback_key": feedback_key,
                "query_id": query_id,
                "analysis_pattern_id": analysis_pattern_id,
                "submitted": True,
                "message": (
                    f"Feedback registrato: {'utile' if success else 'non utile'} "
                    f"({', '.join(updated_targets)})."
                ),
            }
    
        if state.query_feedback_status.get("submitted"):
            return {"display": "block"}, html.Span(
                state.query_feedback_status.get("message"),
                style={"color": "#2ca02c"}
            )
    
        source = suggestion.get("source", "sconosciuta")
        plan_source = getattr(state.current_context, "plan_source", "new")
        confidence_score = getattr(state.current_context, "confidence_score", 0.0)
        similarity_method = getattr(state.current_context, "similarity_method", None)
        return {"display": "block"}, html.Span(
            (
                f"Suggerimento da {source}. Piano analitico: {plan_source}, "
                f"confidence {confidence_score}"
                f"{f', similarita {similarity_method}' if similarity_method else ''}. "
                "In attesa di feedback."
            ),
            style={"color": "#aaa"}
        )
    
    
    # Callback per mostrare chat container
    @app.callback(
        Output('chat-container', 'style'),
        Input('interval-component', 'n_intervals')
    )
    def show_chat_container(n):
        """Mostra la sezione chat quando l'analisi è completata"""
        if state.processing_status.get('status') == 'completed' and state.current_context is not None:
            return {"display": "block"}
        return {"display": "none"}
    
    
    # Callback per download PDF
    @app.callback(
        Output('pdf-download-status', 'children'),
        Output('report-download', 'data'),
        Input('download-pdf-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_pdf(n_clicks):
        """Genera e offre download del PDF"""
        if n_clicks == 0 or state.current_context is None:
            return "", no_update
        
        try:
            logger.info("Generazione PDF richiesta")
            
            # Genera le figure per il PDF
            pdf_path = f"data/reports/report_{uuid.uuid4().hex[:8]}.pdf"
            
            # Estrae i grafici dal context se disponibili
            charts_for_pdf = []
            result_df = state.current_context.raw_data.get("dataframe")
            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                chart_generator = ChartGenerator()
                requested_charts = chart_generator.generate_requested_charts(result_df, state.current_context.user_input)
                automatic_charts = chart_generator.generate_dashboard_charts(
                    result_df,
                    state.current_context.insights,
                )["charts"]
                charts_for_pdf = requested_charts + automatic_charts
            
            # Genera il PDF
            success = state.pdf_generator.generate_report(
                output_path=pdf_path,
                user_input=state.current_context.user_input,
                context={
                    'raw_data': state.current_context.raw_data,
                    'processed_data': state.current_context.processed_data,
                    'insights': state.current_context.insights,
                    'final_report': state.current_context.final_report,
                    'is_valid': state.current_context.is_valid,
                    'errors': state.current_context.errors
                },
                charts_figures=charts_for_pdf,
                title="Multi-Agent Data Analysis Report"
            )
            
            if success:
                logger.info(f"PDF generato: {pdf_path}")
                return (
                    html.Span("✅ Report PDF generato e download avviato.", style={"color": "#2ca02c"}),
                    dcc.send_file(pdf_path),
                )
            else:
                return html.Span(
                    "❌ Errore nella generazione del PDF",
                    style={"color": "#d62728"}
                ), no_update
        
        except Exception as e:
            logger.error(f"Errore download PDF: {type(e).__name__}")
            return html.Span(
                f"❌ Errore: {str(e)}",
                style={"color": "#d62728"}
            ), no_update
    
    
    # Callback per chat follow-up
    @app.callback(
        Output('chat-messages', 'children'),
        Output('chat-input', 'value'),
        Input('interval-component', 'n_intervals'),
        Input('chat-send-button', 'n_clicks'),
        State('chat-input', 'value'),
        running=[(Output('chat-send-button', 'disabled'), True, False)],
        prevent_initial_call=True
    )
    def handle_chat_message(n_intervals, n_clicks, user_message):
        """Gestisce i messaggi della chat follow-up"""

        if ctx.triggered_id == 'interval-component':
            return _render_chat_messages(), no_update

        if not should_process_followup_request(
            n_clicks,
            user_message,
            state.last_processed_n_clicks,
            state.last_followup_request_id,
        ):
            return _render_chat_messages(), no_update

        request_id = build_followup_request_id(n_clicks, user_message)
        with state.followup_lock:
            if state.followup_processing:
                return _render_chat_messages(), no_update
            if not should_process_followup_request(
                n_clicks,
                user_message,
                state.last_processed_n_clicks,
                state.last_followup_request_id,
            ):
                return _render_chat_messages(), no_update
            state.followup_processing = True
            state.last_processed_n_clicks = int(n_clicks or 0)
            state.last_followup_request_id = request_id
        
        try:
            # Inizializza conversation manager se necessario
            if state.conversation_manager is None:
                state.conversation_manager = ConversationManager(session_id=str(uuid.uuid4()))
                state.conversation_agent = ConversationAgent()
                
                if state.current_context:
                    state.conversation_manager.set_analysis_context({
                        'raw_data': state.current_context.raw_data,
                        'processed_data': state.current_context.processed_data,
                        'insights': state.current_context.insights,
                        'is_valid': state.current_context.is_valid,
                        'errors': state.current_context.errors
                    })
            
            # Aggiunge messaggio utente
            state.conversation_manager.add_user_message(user_message)
            logger.info(f"Domanda follow-up: {user_message[:50]}")
    
            chart_result = try_generate_followup_chart(user_message, state.current_context)
            if chart_result:
                state.followup_charts.append(chart_result)
                state.conversation_manager.add_assistant_message(chart_result["message"])
                state.followup_processing = False
                return _render_chat_messages(), ""
    
            analysis_result = try_run_followup_analysis(user_message, state.current_context)
            if analysis_result:
                if analysis_result.get("context") is not None:
                    state.current_context = analysis_result["context"]
                    result_df = state.current_context.raw_data.get("dataframe")
                    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                        state.current_charts = ChartGenerator.generate_dashboard_charts(
                            result_df,
                            state.current_context.insights,
                        )["charts"]
                if analysis_result.get("chart"):
                    state.followup_charts.append({
                        "figure": analysis_result["chart"],
                        "description": analysis_result["description"],
                })
                state.conversation_manager.add_assistant_message(analysis_result["message"])
                state.followup_processing = False
                return _render_chat_messages(), ""
            
            try:
                response = state.conversation_agent.answer_followup_question(
                    question=user_message,
                    previous_context={
                        'raw_data': state.current_context.raw_data,
                        'processed_data': state.current_context.processed_data,
                        'insights': state.current_context.insights,
                        'is_valid': state.current_context.is_valid,
                        'errors': state.current_context.errors
                    },
                    conversation_history=state.conversation_manager.get_chat_history()
                )
                state.conversation_manager.add_assistant_message(response)
            except Exception as e:
                logger.error(f"Errore generazione risposta: {type(e).__name__}")
                state.conversation_manager.add_assistant_message(f"❌ Errore nella risposta: {str(e)}")
            finally:
                state.followup_processing = False
            
            # Costruisce il display dei messaggi
            messages_html = []
            for msg in state.conversation_manager.messages:
                if msg.role == "user":
                    messages_html.append(html.Div([
                        html.Span("👤 Tu: ", style={"fontWeight": "bold", "color": "#1f77b4"}),
                        html.Span(msg.content)
                    ], style={"marginBottom": "10px", "padding": "8px", "backgroundColor": "rgba(31, 119, 180, 0.1)", "borderRadius": "8px"}))
                else:
                    messages_html.append(html.Div([
                        html.Span("🤖 Assistente: ", style={"fontWeight": "bold", "color": "#ff7f0e"}),
                        html.Span(msg.content)
                    ], style={"marginBottom": "10px", "padding": "8px", "backgroundColor": "rgba(255, 127, 14, 0.1)", "borderRadius": "8px"}))
            
            return _render_chat_messages(), ""
        
        except Exception as e:
            state.followup_processing = False
            logger.error(f"Errore gestione chat: {type(e).__name__}")
            return [html.Div([
                html.Span("❌ Errore: ", style={"color": "#d62728"}),
                html.Span(str(e))
            ])], no_update
    
    def _render_chat_messages():
        """Costruisce il rendering della chat corrente."""
        if state.conversation_manager is None:
            return []
    
        messages_html = []
        for msg in state.conversation_manager.messages:
            if msg.role == "user":
                messages_html.append(html.Div([
                    html.Span("Tu: ", style={"fontWeight": "bold", "color": "#1f77b4"}),
                    html.Span(msg.content)
                ], style={"marginBottom": "10px", "padding": "8px", "backgroundColor": "rgba(31, 119, 180, 0.1)", "borderRadius": "8px"}))
            else:
                messages_html.append(html.Div([
                    html.Span("Assistente: ", style={"fontWeight": "bold", "color": "#ff7f0e"}),
                    html.Span(msg.content)
                ], style={"marginBottom": "10px", "padding": "8px", "backgroundColor": "rgba(255, 127, 14, 0.1)", "borderRadius": "8px"}))
    
        return messages_html
