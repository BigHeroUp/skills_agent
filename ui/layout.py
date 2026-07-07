"""Layout Dash della dashboard multi-agent."""

import uuid

from dash import dcc, html


DASH_INDEX_STRING = '''
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
                position: relative;
            }
            
            .agent-step {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border-left: 4px solid rgba(255, 255, 255, 0.14);
                transition: background-color 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
            }
            
            .agent-step.active {
                background: rgba(31, 119, 180, 0.16);
                border-left-color: #4aa3df;
                box-shadow: inset 0 0 0 1px rgba(74, 163, 223, 0.35), 0 0 18px rgba(74, 163, 223, 0.18);
            }
            
            .agent-step.completed {
                background: rgba(44, 160, 44, 0.16);
                border-left-color: #2ca02c;
            }

            .agent-step.error {
                background: rgba(214, 39, 40, 0.16);
                border-left-color: #d62728;
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
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.74);
            }
            
            .status-badge.active {
                background: rgba(31, 119, 180, 0.24);
                color: #9ed8ff;
                box-shadow: 0 0 16px rgba(74, 163, 223, 0.2);
            }
            
            .status-badge.completed {
                background: rgba(44, 160, 44, 0.3);
                color: #7ee787;
            }

            .status-badge.error {
                background: rgba(214, 39, 40, 0.24);
                color: #ff9b9b;
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
                width: 0%;
                transition: width 0.7s ease;
                box-shadow: 0 0 14px rgba(74, 163, 223, 0.28);
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
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @media (prefers-reduced-motion: reduce) {
                .header,
                .card,
                .agent-step,
                .progress-fill {
                    animation: none !important;
                    transition: none !important;
                }
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


def create_layout(processing_status):
    """Crea il layout Dash mantenendo gli stessi component id pubblici."""
    return html.Div([
        dcc.Store(id='session-id', data=str(uuid.uuid4())),
        dcc.Store(id='processing-store', data=processing_status),
        dcc.Store(id='context-store', data=None),
        dcc.Store(id='charts-store', data=None),
        dcc.Store(id='oracle-connection-store', data={"verified": False}),
        dcc.Download(id='report-download'),
        dcc.Interval(id='interval-component', interval=500, n_intervals=0, disabled=True),
        
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
            
            # Report finale e insight prima dei grafici
            html.Div([
                html.Div([
                    html.H3("📋 Executive Summary, KPI e Business Findings"),
                    html.Div(id='final-report', style={"whiteSpace": "pre-wrap", "lineHeight": "1.6"}),
                    html.Button(
                        "📥 Scarica Report PDF",
                        id='download-pdf-button',
                        n_clicks=0,
                        className='secondary-button',
                        style={"marginTop": "15px"}
                    ),
                    html.Div(id='pdf-download-status', style={"marginTop": "10px"}),
                    html.Div([
                        html.H4("Feedback suggerimento query", style={"marginTop": "22px", "marginBottom": "10px"}),
                        html.Div(
                            "Indica se il suggerimento usato per l'estrazione e stato utile.",
                            style={"color": "#aaa", "marginBottom": "12px"}
                        ),
                        html.Div([
                            html.Button(
                                "Utile",
                                id='feedback-useful-button',
                                n_clicks=0,
                                className='secondary-button',
                                style={"marginRight": "10px", "width": "auto"}
                            ),
                            html.Button(
                                "Non utile",
                                id='feedback-not-useful-button',
                                n_clicks=0,
                                className='secondary-button',
                                style={"background": "#6c757d", "width": "auto"}
                            ),
                        ]),
                        html.Div(id='query-feedback-status', style={"marginTop": "10px"})
                    ], id='query-feedback-container', style={"display": "none"})
                ], className="card")
            ], id='report-container', style={"display": "none"}),

            # Grafici utili dopo gli insight
            html.Div([
                html.Div([
                    html.H3("📈 Grafici utili"),
                    html.Div(id='charts-container', className="charts-grid")
                ], className="card")
            ], id='results-container', style={"display": "none"}),

            # Knowledge Graph Explorer
            html.Div([
                html.Div([
                    html.Div([
                        html.Div([
                            html.H3("Knowledge Graph Explorer"),
                            html.P(
                                "Lineage visuale dell'ultima analisi salvata nel Knowledge Graph.",
                                style={"color": "#aaa", "marginTop": "6px"}
                            ),
                        ]),
                        html.Button(
                            "Aggiorna grafo",
                            id='knowledge-graph-refresh-button',
                            n_clicks=0,
                            className='secondary-button',
                            style={"width": "auto"}
                        ),
                    ], style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "gap": "16px",
                        "flexWrap": "wrap",
                    }),
                    html.Div(id='knowledge-graph-status', style={"color": "#9ed8ff", "marginTop": "12px"}),
                    dcc.Graph(
                        id='knowledge-graph-figure',
                        config={"displayModeBar": True, "responsive": True},
                        style={"marginTop": "12px"}
                    ),
                    html.Div([
                        html.H4("Dettaglio nodo", style={"marginBottom": "10px"}),
                        html.Div(
                            "Seleziona un nodo nel grafo per vedere type, id e properties principali.",
                            id='knowledge-graph-node-details',
                            style={"color": "#aaa", "lineHeight": "1.55"}
                        )
                    ], style={
                        "marginTop": "16px",
                        "padding": "14px",
                        "border": "1px solid rgba(255,255,255,0.12)",
                        "borderRadius": "8px",
                        "background": "rgba(0,0,0,0.22)",
                    })
                ], className="card")
            ], id='knowledge-graph-container', style={"display": "none"}),
            
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
