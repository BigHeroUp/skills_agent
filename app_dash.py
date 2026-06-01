"""
Applicazione Dash con UX professionale
Dashboard per visualizzare il flusso multi-agente e i grafici
"""

import dash
from dash import dcc, html, Input, Output, State, callback, ctx
from connectors.data_connectors import DataSourceFactory
from coordinator import Coordinator
from utils.chart_generator import ChartGenerator
from utils.logging_config import get_logger
from utils.pdf_generator import PDFGenerator
from utils.conversation_manager import ConversationManager
from agents.conversation_agent import ConversationAgent
import pandas as pd
import threading
import json
import uuid
import base64
import io
from pathlib import Path


# Inizializza l'app Dash
app = dash.Dash(__name__)
app.title = "Multi-Agent Data Analysis Platform"

# Store per conservare i dati tra ricariche
coordinator = None
current_context = None
processing_status = {"status": "idle", "current_agent": "", "progress": 0}
uploaded_df = None
oracle_connection_config = None
logger = get_logger("dashboard")

# Conversazione e PDF
conversation_manager: ConversationManager = None
conversation_agent: ConversationAgent = None
pdf_generator: PDFGenerator = PDFGenerator()
current_charts = []  # Conserva i chart per PDF


# Layout CSS personalizzato
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary: #1f77b4;
                --secondary: #ff7f0e;
                --success: #2ca02c;
                --danger: #d62728;
                --dark: #1a1a1a;
                --light: #f8f9fa;
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, var(--dark) 0%, #2d2d2d 100%);
                color: #fff;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
                animation: slideDown 0.8s ease-out;
            }
            
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #1f77b4, #ff7f0e);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
                animation: fadeIn 0.6s ease-out;
            }

            .source-picker label {
                color: #f8f9fa !important;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
            }

            .source-picker input {
                accent-color: #4aa3df;
                margin-right: 6px;
            }

            .form-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin: 18px 0;
            }

            .form-field label {
                display: block;
                color: #f8f9fa;
                margin-bottom: 8px;
                font-weight: 600;
            }

            .form-input {
                width: 100%;
                min-height: 46px;
                padding: 11px 12px;
                color: #fff;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }

            .form-input::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }

            .form-input:focus,
            .analysis-textarea:focus {
                outline: none;
                border-color: #4aa3df;
                box-shadow: 0 0 0 3px rgba(74, 163, 223, 0.22);
            }

            .analysis-textarea {
                width: 100%;
                min-height: 96px;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                background: rgba(255, 255, 255, 0.08);
                color: #fff;
                font-size: 16px;
                resize: vertical;
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }

            .analysis-textarea::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }

            .upload-dropzone {
                width: 100%;
                min-height: 104px;
                padding: 34px 16px;
                border: 2px dashed #4aa3df;
                border-radius: 10px;
                text-align: center;
                cursor: pointer;
                background: rgba(31, 119, 180, 0.12);
                color: #f8f9fa;
            }

            .upload-dropzone a {
                color: #73c6ff;
                font-weight: 600;
            }

            .secondary-button {
                min-height: 46px;
                padding: 11px 22px;
                background: #1f77b4;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                cursor: pointer;
            }

            .primary-button {
                width: 100%;
                min-height: 50px;
                margin-top: 22px;
                padding: 12px 30px;
                background: linear-gradient(135deg, #1f77b4, #ff7f0e);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
            }

            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .agent-timeline {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .agent-step {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                animation: slideIn 0.4s ease-out;
            }
            
            .agent-step.active {
                background: rgba(31, 119, 180, 0.2);
                border-left: 4px solid #1f77b4;
            }
            
            .agent-step.completed {
                background: rgba(44, 160, 44, 0.2);
                border-left: 4px solid #2ca02c;
            }
            
            .agent-icon {
                font-size: 1.5em;
                min-width: 30px;
                text-align: center;
            }
            
            .agent-name {
                flex: 1;
                font-weight: 600;
            }
            
            .status-badge {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }
            
            .status-badge.pending {
                background: rgba(255, 127, 14, 0.3);
                color: #ff7f0e;
            }
            
            .status-badge.active {
                background: rgba(31, 119, 180, 0.3);
                color: #1f77b4;
                animation: pulse 1.5s infinite;
            }
            
            .status-badge.completed {
                background: rgba(44, 160, 44, 0.3);
                color: #2ca02c;
            }
            
            .progress-bar {
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                overflow: hidden;
                margin-top: 20px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #1f77b4, #ff7f0e);
                border-radius: 2px;
                animation: slideRight 2s ease-in-out infinite;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @keyframes slideRight {
                0%, 100% { width: 0%; }
                50% { width: 100%; }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            .charts-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            
            .chart-card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
                backdrop-filter: blur(10px);
            }

            @media (max-width: 720px) {
                .container {
                    padding: 12px;
                }

                .header {
                    margin-bottom: 22px;
                }

                .header h1 {
                    font-size: 1.75em;
                }

                .card {
                    padding: 16px;
                }

                .source-picker {
                    flex-direction: column;
                    gap: 8px !important;
                    margin-top: 12px;
                }

                .source-picker label {
                    display: block;
                    width: 100%;
                }

                .form-grid {
                    grid-template-columns: 1fr;
                    gap: 12px;
                }

                .upload-dropzone {
                    min-height: 88px;
                    padding: 25px 12px;
                    line-height: 1.45;
                }

                .secondary-button,
                .primary-button {
                    width: 100%;
                }

                .charts-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout
app.layout = html.Div([
    dcc.Store(id='session-id', data=str(uuid.uuid4())),
    dcc.Store(id='processing-store', data=processing_status),
    dcc.Store(id='context-store', data=None),
    dcc.Store(id='charts-store', data=None),
    dcc.Store(id='oracle-connection-store', data={"verified": False}),
    dcc.Interval(id='interval-component', interval=500, n_intervals=0),
    
    html.Div([
        # Header
        html.Div([
            html.H1("🤖 Multi-Agent Data Analysis Platform"),
            html.P("Sistema intelligente per analisi dati multi-sorgente")
        ], className="header"),
        
        # Selezione fonte dati
        html.Div([
            html.Div([
                html.H3("📊 Seleziona Fonte Dati"),
                
                html.Div([
                    html.Label("Tipo di Fonte:", style={"marginRight": "20px"}),
                    dcc.RadioItems(
                        id='source-type',
                        options=[
                            {'label': ' 🗄️ Oracle Database', 'value': 'oracle'},
                            {'label': ' 📄 CSV', 'value': 'csv'},
                            {'label': ' 📊 Excel', 'value': 'excel'}
                        ],
                        value='csv',
                        inline=True,
                        className="source-picker",
                        style={"display": "flex", "gap": "30px"}
                    )
                ], style={"marginBottom": "20px"}),
                
                # Upload file
                html.Div(id='file-upload-container', children=[
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['📁 Trascina il file qui o ', html.A('clicca per selezionare')]),
                        className='upload-dropzone',
                        multiple=False
                    ),
                    html.Div(id='upload-status', style={"marginTop": "10px"})
                ]),

                # Connessione Oracle
                html.Div(id='oracle-config-container', children=[
                    html.Div([
                        html.Div([
                            html.Label("Host"),
                            dcc.Input(id='oracle-host', type='text', placeholder='es. db.example.local', className='form-input')
                        ], className='form-field'),
                        html.Div([
                            html.Label("Porta"),
                            dcc.Input(id='oracle-port', type='number', value=1521, min=1, max=65535, className='form-input')
                        ], className='form-field'),
                        html.Div([
                            html.Label("Service name / Database"),
                            dcc.Input(id='oracle-database', type='text', placeholder='es. ORCLPDB1', className='form-input')
                        ], className='form-field'),
                        html.Div([
                            html.Label("Utente"),
                            dcc.Input(id='oracle-user', type='text', placeholder='Username', className='form-input')
                        ], className='form-field'),
                        html.Div([
                            html.Label("Password"),
                            dcc.Input(id='oracle-password', type='password', placeholder='Password', className='form-input')
                        ], className='form-field'),
                    ], className='form-grid'),
                    html.Button("Verifica connessione", id='test-oracle-button', n_clicks=0, className='secondary-button'),
                    html.Div(id='oracle-connection-status', style={"marginTop": "12px"})
                ], style={"display": "none"}),
                
                # Descrizione analisi
                html.Div(id='analysis-container', children=[
                    html.Div(id='oracle-query-container', children=[
                        html.Label("Query dati Oracle (solo SELECT o WITH):"),
                        dcc.Textarea(
                            id='oracle-query',
                            placeholder='SELECT colonna1, colonna2 FROM tabella FETCH FIRST 1000 ROWS ONLY',
                            className='analysis-textarea',
                            style={'marginTop': '10px', 'marginBottom': '18px'}
                        )
                    ], style={"display": "none"}),
                    html.Label("Descrivi l'analisi che vuoi fare:"),
                    dcc.Textarea(
                        id='analysis-description',
                        placeholder='Es. Analizza i trend di vendita per trimestre e regione...',
                        className='analysis-textarea',
                        style={'marginTop': '10px'}
                    )
                ], style={"marginTop": "20px"}),
                
                # Bottone avvio
                html.Button(
                    "🚀 Avvia Analisi",
                    id='start-button',
                    n_clicks=0,
                    className='primary-button'
                )
            ], className="card")
        ]),
        
        # Timeline agenti
        html.Div([
            html.Div([
                html.H3("🔄 Flusso di Elaborazione"),
                html.Div(id='agent-timeline', className="agent-timeline"),
                html.Div(id='progress-container', children=[
                    html.Div(className="progress-bar", children=[
                        html.Div(id='progress-fill', className="progress-fill")
                    ])
                ], style={"display": "none"})
            ], className="card")
        ], id='timeline-container', style={"display": "none"}),
        
        # Risultati e grafici
        html.Div([
            html.Div([
                html.H3("📈 Grafici Analisi"),
                html.Div(id='charts-container', className="charts-grid")
            ], className="card")
        ], id='results-container', style={"display": "none"}),
        
        # Report finale
        html.Div([
            html.Div([
                html.H3("📋 Report Finale"),
                html.Div(id='final-report', style={"whiteSpace": "pre-wrap", "lineHeight": "1.6", "maxHeight": "400px", "overflowY": "auto"}),
                html.Button(
                    "📥 Scarica Report PDF",
                    id='download-pdf-button',
                    n_clicks=0,
                    className='secondary-button',
                    style={"marginTop": "15px"}
                ),
                html.Div(id='pdf-download-status', style={"marginTop": "10px"})
            ], className="card")
        ], id='report-container', style={"display": "none"}),
        
        # Sezione Chat Follow-up
        html.Div([
            html.Div([
                html.H3("💬 Domande di Follow-up"),
                html.P("Fai ulteriori domande sull'analisi appena completata", style={"color": "#aaa"}),
                html.Div(id='chat-messages', style={
                    "height": "400px",
                    "overflowY": "auto",
                    "border": "1px solid rgba(255,255,255,0.2)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "marginBottom": "15px",
                    "backgroundColor": "rgba(0,0,0,0.3)"
                }, children=[]),
                html.Div([
                    dcc.Input(
                        id='chat-input',
                        type='text',
                        placeholder='Fai una domanda sulla tua analisi...',
                        className='form-input',
                        style={"marginBottom": "10px"}
                    ),
                    html.Button(
                        "Invia",
                        id='chat-send-button',
                        n_clicks=0,
                        className='secondary-button',
                        style={"width": "100%"}
                    )
                ])
            ], className="card")
        ], id='chat-container', style={"display": "none"}),
        
    ], className="container")
], style={"minHeight": "100vh", "paddingBottom": "50px"})


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
    global oracle_connection_config

    if ctx.triggered_id != 'test-oracle-button':
        oracle_connection_config = None
        logger.info("Configurazione Oracle modificata: verifica connessione invalidata")
        return html.Span(
            "Verifica nuovamente la connessione dopo aver modificato i parametri.",
            style={"color": "#ffbf69"}
        ), {"verified": False}

    required_values = [host, port, database, user, password]
    if not all(required_values):
        oracle_connection_config = None
        logger.warning("Test Oracle non avviato: parametri incompleti")
        return html.Span(
            "Compila tutti i parametri Oracle prima della verifica.",
            style={"color": "#ff6b6b"}
        ), {"verified": False}

    connector = None
    try:
        logger.info("Test Oracle richiesto dalla dashboard")
        connector = DataSourceFactory.create_connector(
            "oracle",
            host=host.strip(),
            port=int(port),
            database=database.strip(),
            user=user.strip(),
            password=password,
        )
        connector.test_connection()
        oracle_connection_config = {
            "host": host.strip(),
            "port": int(port),
            "database": database.strip(),
            "user": user.strip(),
            "password": password,
        }
        logger.info("Test Oracle riuscito")
        return html.Span(
            "Connessione Oracle verificata. Puoi configurare l'analisi.",
            style={"color": "#52d273"}
        ), {"verified": True}
    except Exception as e:
        oracle_connection_config = None
        logger.error("Test Oracle fallito: %s", type(e).__name__)
        return html.Span(
            f"Connessione non riuscita: {str(e)}",
            style={"color": "#ff6b6b"}
        ), {"verified": False}
    finally:
        if connector:
            connector.close()


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
        global uploaded_df
        
        # Decodifica il file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if source_type == 'csv':
            uploaded_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif source_type == 'excel':
            uploaded_df = pd.read_excel(io.BytesIO(decoded))
        else:
            raise ValueError("Il caricamento file è disponibile solo per CSV o Excel.")

        logger.info(
            "File caricato. source_type=%s nome=%s righe=%s colonne=%s dimensione_mb=%.2f",
            source_type,
            filename,
            len(uploaded_df),
            len(uploaded_df.columns),
            len(decoded) / (1024 * 1024),
        )
        
        status = html.Div([
            html.Span("✅ File caricato: ", style={"color": "#2ca02c"}),
            html.Span(f"{filename} ({len(uploaded_df)} righe, {len(uploaded_df.columns)} colonne)")
        ])
        
        # Prepara context metadata
        metadata = {
            "source_type": source_type,
            "file_path": filename,
            "file_size_mb": len(decoded) / (1024 * 1024)
        }
        
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
    global processing_status

    if not description:
        logger.warning("Analisi non avviata: descrizione mancante")
        return {"display": "none"}, processing_status

    if source_type == 'oracle':
        if not oracle_state.get("verified") or not oracle_connection_config or not oracle_query:
            logger.warning("Analisi Oracle non avviata: connessione o query non verificate")
            return {"display": "none"}, processing_status
    elif not context_metadata:
        logger.warning("Analisi non avviata: nessun file caricato. source_type=%s", source_type)
        return {"display": "none"}, processing_status

    processing_status = {
        "status": "processing",
        "current_agent": "DataSourceManager",
        "progress": 0,
    }
    logger.info("Analisi richiesta dalla dashboard. source_type=%s", source_type)
    
    def run_pipeline():
        global processing_status, current_context
        
        try:
            # Prepara il context
            if source_type == 'oracle':
                metadata = {
                    "source_type": "oracle",
                    "oracle_config": oracle_connection_config.copy(),
                    "oracle_query": oracle_query.strip(),
                }
            else:
                metadata = json.loads(context_metadata)
                metadata["source_type"] = source_type

                # Se è upload, passa il dataframe
                if uploaded_df is not None:
                    metadata["dataframe"] = uploaded_df
            
            # Esegui il pipeline
            coordinator_instance = Coordinator()
            def update_progress(agent_name, progress):
                processing_status["current_agent"] = agent_name
                processing_status["progress"] = progress

            current_context = coordinator_instance.run(
                description,
                metadata=metadata,
                progress_callback=update_progress,
            )
            
            processing_status["status"] = "completed"
            processing_status["current_agent"] = "Completato"
            processing_status["progress"] = 100
            logger.info("Analisi dashboard completata. source_type=%s", source_type)
            
        except Exception as e:
            processing_status["status"] = "error"
            processing_status["error"] = str(e)
            logger.error("Analisi dashboard fallita. source_type=%s errore=%s", source_type, type(e).__name__)
    
    # Esegui in thread parallelo
    thread = threading.Thread(target=run_pipeline)
    thread.daemon = True
    thread.start()
    
    return {"display": "block"}, processing_status.copy()


# Callback per update timeline
@app.callback(
    Output('agent-timeline', 'children'),
    Output('progress-container', 'style'),
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
    
    status = processing_status.get('status', 'idle')
    current_agent = processing_status.get('current_agent', '')
    
    if status == 'idle':
        return [], {"display": "none"}
    
    timeline = []
    for i, agent in enumerate(agents):
        if agent == current_agent:
            badge_class = "active"
            icon = "⚙️"
            status_text = "In elaborazione"
        elif status == 'completed':
            badge_class = "completed"
            icon = "✅"
            status_text = "Completato"
        else:
            badge_class = "pending"
            icon = "⏳"
            status_text = "In attesa"
        
        step_class = "agent-step"
        if badge_class == 'active':
            step_class += " active"
        elif badge_class == 'completed':
            step_class += " completed"
        
        timeline.append(
            html.Div([
                html.Div(icon, className="agent-icon"),
                html.Div(agent, className="agent-name"),
                html.Div(status_text, className=f"status-badge {badge_class}")
            ], className=step_class)
        )
    
    progress_style = {"display": "block"} if status == 'processing' else {"display": "none"}
    
    return timeline, progress_style


# Callback per mostrare risultati
@app.callback(
    Output('final-report', 'children'),
    Output('report-container', 'style'),
    Output('charts-container', 'children'),
    Output('results-container', 'style'),
    Input('interval-component', 'n_intervals')
)
def display_results(n):
    if processing_status.get('status') != 'completed' or current_context is None:
        return "", {"display": "none"}, [], {"display": "none"}
    
    try:
        # Mostra il report
        report_text = current_context.final_report if current_context.final_report else "Analisi completata"
        
        # Genera grafici se ci sono dati
        charts_html = []
        result_df = current_context.raw_data.get("dataframe")
        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            chart_generator = ChartGenerator()
            charts = chart_generator.auto_generate_charts(result_df, current_context.insights)
            
            for chart in charts:
                charts_html.append(
                    html.Div([dcc.Graph(figure=chart)], className="chart-card")
                )
        
        return report_text, {"display": "block"}, charts_html, {"display": "block"}
    
    except Exception as e:
        logger.error("Visualizzazione risultati fallita: %s", type(e).__name__)
        return f"❌ Errore nella visualizzazione: {str(e)}", {"display": "block"}, [], {"display": "none"}


# Callback per mostrare chat container
@app.callback(
    Output('chat-container', 'style'),
    Input('interval-component', 'n_intervals')
)
def show_chat_container(n):
    """Mostra la sezione chat quando l'analisi è completata"""
    if processing_status.get('status') == 'completed' and current_context is not None:
        return {"display": "block"}
    return {"display": "none"}


# Callback per download PDF
@app.callback(
    Output('pdf-download-status', 'children'),
    Input('download-pdf-button', 'n_clicks'),
    prevent_initial_call=True
)
def download_pdf(n_clicks):
    """Genera e offre download del PDF"""
    if n_clicks == 0 or current_context is None:
        return ""
    
    try:
        logger.info("Generazione PDF richiesta")
        
        # Genera le figure per il PDF
        pdf_path = f"data/reports/report_{uuid.uuid4().hex[:8]}.pdf"
        
        # Estrae i grafici dal context se disponibili
        charts_for_pdf = []
        result_df = current_context.raw_data.get("dataframe")
        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            chart_generator = ChartGenerator()
            charts_for_pdf = chart_generator.auto_generate_charts(result_df, current_context.insights)
        
        # Genera il PDF
        success = pdf_generator.generate_report(
            output_path=pdf_path,
            user_input=current_context.user_input,
            context={
                'raw_data': current_context.raw_data,
                'processed_data': current_context.processed_data,
                'insights': current_context.insights,
                'final_report': current_context.final_report,
                'is_valid': current_context.is_valid,
                'errors': current_context.errors
            },
            charts_figures=charts_for_pdf,
            title="Multi-Agent Data Analysis Report"
        )
        
        if success:
            logger.info(f"PDF generato: {pdf_path}")
            return html.Div([
                html.Span("✅ Report PDF generato con successo!", style={"color": "#2ca02c"}),
                html.Br(),
                html.A(
                    "📥 Scarica PDF",
                    href=f"data/reports/report_{uuid.uuid4().hex[:8]}.pdf",
                    download=True,
                    style={"color": "#1f77b4", "textDecoration": "underline"}
                )
            ])
        else:
            return html.Span(
                "❌ Errore nella generazione del PDF",
                style={"color": "#d62728"}
            )
    
    except Exception as e:
        logger.error(f"Errore download PDF: {type(e).__name__}")
        return html.Span(
            f"❌ Errore: {str(e)}",
            style={"color": "#d62728"}
        )


# Callback per chat follow-up
@app.callback(
    Output('chat-messages', 'children'),
    Input('chat-send-button', 'n_clicks'),
    State('chat-input', 'value'),
    prevent_initial_call=True
)
def handle_chat_message(n_clicks, user_message):
    """Gestisce i messaggi della chat follow-up"""
    global conversation_manager, conversation_agent, current_context
    
    if n_clicks == 0 or not user_message or not user_message.strip():
        return []
    
    try:
        # Inizializza conversation manager se necessario
        if conversation_manager is None:
            conversation_manager = ConversationManager(session_id=str(uuid.uuid4()))
            conversation_agent = ConversationAgent()
            
            if current_context:
                conversation_manager.set_analysis_context({
                    'raw_data': current_context.raw_data,
                    'processed_data': current_context.processed_data,
                    'insights': current_context.insights,
                    'is_valid': current_context.is_valid,
                    'errors': current_context.errors
                })
        
        # Aggiunge messaggio utente
        conversation_manager.add_user_message(user_message)
        logger.info(f"Domanda follow-up: {user_message[:50]}")
        
        # Genera risposta in background
        def generate_response():
            try:
                response = conversation_agent.answer_followup_question(
                    question=user_message,
                    previous_context={
                        'raw_data': current_context.raw_data,
                        'processed_data': current_context.processed_data,
                        'insights': current_context.insights,
                        'is_valid': current_context.is_valid,
                        'errors': current_context.errors
                    },
                    conversation_history=conversation_manager.get_chat_history()
                )
                conversation_manager.add_assistant_message(response)
            except Exception as e:
                logger.error(f"Errore generazione risposta: {type(e).__name__}")
                conversation_manager.add_assistant_message(f"❌ Errore nella risposta: {str(e)}")
        
        # Esegui in thread
        thread = threading.Thread(target=generate_response)
        thread.daemon = True
        thread.start()
        
        # Costruisce il display dei messaggi
        messages_html = []
        for msg in conversation_manager.messages:
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
        
        return messages_html
    
    except Exception as e:
        logger.error(f"Errore gestione chat: {type(e).__name__}")
        return [html.Div([
            html.Span("❌ Errore: ", style={"color": "#d62728"}),
            html.Span(str(e))
        ])]


if __name__ == '__main__':
    app.run(debug=True, port=8050)

