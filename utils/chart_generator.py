"""
Modulo per generazione automatica grafici
Analizza i dati e crea grafici Plotly appropriati
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from utils.logging_config import get_logger


logger = get_logger("charts")


class ChartGenerator:
    """Genera grafici automatici dai dati"""

    @staticmethod
    def generate_requested_charts(df: pd.DataFrame, user_request: str) -> List[go.Figure]:
        """Genera grafici specifici richiesti dall'utente quando riconoscibili."""
        charts: List[go.Figure] = []
        if not isinstance(df, pd.DataFrame) or df.empty or not user_request:
            return charts

        request = user_request.lower()
        wants_status_counts = (
            any(term in request for term in ["stato", "stati", "status", "state"])
            and any(term in request for term in ["occorren", "conteggio", "quanti", "totale", "somma"])
        )
        wants_bar = any(term in request for term in ["colonne", "barre", "bar chart", "grafico a colonna"])
        wants_trend = any(term in request for term in ["andamento", "trend", "evoluzione", "nel tempo", "temporale"])

        if wants_status_counts or (wants_bar and any(term in request for term in ["ticket", "stato", "status"])):
            status_col = ChartGenerator._find_status_column(df)
            if status_col:
                charts.append(ChartGenerator._status_occurrence_chart(df, status_col))

        if wants_trend:
            trend_chart = ChartGenerator._ticket_trend_chart(df)
            if trend_chart is not None:
                charts.append(trend_chart)

        return charts
    
    @staticmethod
    def auto_generate_charts(df: pd.DataFrame, insights: Dict[str, Any]) -> List[go.Figure]:
        """
        Genera automaticamente grafici appropriati in base ai dati
        """
        charts = []
        
        try:
            # Identifica colonne numeriche e categoriche
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            
            # 1. Distribuzione delle colonne numeriche
            if numeric_cols:
                for col in numeric_cols[:3]:  # Primi 3
                    fig = px.histogram(
                        df, 
                        x=col,
                        title=f"📊 Distribuzione {col}",
                        nbins=30,
                        labels={col: col},
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig.update_layout(
                        template='plotly_dark',
                        showlegend=False,
                        height=400
                    )
                    charts.append(fig)
            
            # 2. Correlazione tra variabili numeriche
            if len(numeric_cols) >= 2:
                corr_matrix = df[numeric_cols].corr()
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu',
                    zmid=0
                ))
                fig.update_layout(
                    title="🔥 Matrice Correlazione",
                    template='plotly_dark',
                    height=400
                )
                charts.append(fig)
            
            # 3. Top valori per colonna categorica
            if categorical_cols:
                col = categorical_cols[0]
                top_values = df[col].value_counts().head(10)
                fig = px.bar(
                    x=top_values.values,
                    y=top_values.index,
                    orientation='h',
                    title=f"📈 Top 10 {col}",
                    labels={'x': 'Conteggio', 'y': col},
                    color=top_values.values,
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(
                    template='plotly_dark',
                    height=400,
                    showlegend=False
                )
                charts.append(fig)
            
            # 4. Serie temporale se presente colonna data
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            if date_cols and numeric_cols:
                date_col = date_cols[0]
                numeric_col = numeric_cols[0]
                try:
                    df_sorted = df[[date_col, numeric_col]].sort_values(date_col)
                    fig = px.line(
                        df_sorted,
                        x=date_col,
                        y=numeric_col,
                        title=f"📅 Trend {numeric_col}",
                        labels={date_col: 'Data', numeric_col: numeric_col}
                    )
                    fig.update_layout(
                        template='plotly_dark',
                        height=400
                    )
                    charts.append(fig)
                except:
                    pass
            
            # 5. Box plot per valori anomali
            if numeric_cols:
                fig = go.Figure()
                for col in numeric_cols[:3]:
                    fig.add_trace(go.Box(
                        y=df[col],
                        name=col,
                        boxmean='sd'
                    ))
                fig.update_layout(
                    title="📦 Analisi Anomalie (Box Plot)",
                    template='plotly_dark',
                    height=400
                )
                charts.append(fig)
            
            # 6. Statistiche riassuntive
            if numeric_cols:
                stats_data = df[numeric_cols].describe().T
                fig = go.Figure(data=[go.Table(
                    header=dict(
                        values=['Colonna', 'Media', 'Std', 'Min', 'Max'],
                        fill_color='rgba(31, 119, 180, 0.3)',
                        align='left'
                    ),
                    cells=dict(
                        values=[
                            stats_data.index,
                            stats_data['mean'].round(2),
                            stats_data['std'].round(2),
                            stats_data['min'].round(2),
                            stats_data['max'].round(2)
                        ],
                        fill_color='rgba(255, 255, 255, 0.05)',
                        align='left'
                    )
                )])
                fig.update_layout(
                    title="📋 Statistiche Dati",
                    template='plotly_dark',
                    height=300
                )
                charts.append(fig)
            
        except Exception as e:
            logger.error("Generazione grafici fallita: %s", type(e).__name__)
            print(f"⚠️ Errore generazione grafici: {e}")
        
        return charts

    @staticmethod
    def _status_occurrence_chart(df: pd.DataFrame, status_col: str) -> go.Figure:
        counts = (
            df[status_col]
            .fillna("N/D")
            .astype(str)
            .value_counts(dropna=False)
            .reset_index()
        )
        counts.columns = [str(status_col), "Occorrenze"]

        fig = px.bar(
            counts,
            x=str(status_col),
            y="Occorrenze",
            title=f"Occorrenze per {status_col}",
            labels={str(status_col): str(status_col), "Occorrenze": "Occorrenze"},
            text="Occorrenze",
            color="Occorrenze",
            color_continuous_scale="Blues",
        )
        fig.update_layout(template="plotly_dark", height=460, xaxis_tickangle=-35, showlegend=False)
        fig.update_traces(textposition="outside")
        return fig

    @staticmethod
    def _ticket_trend_chart(df: pd.DataFrame) -> go.Figure | None:
        date_col = ChartGenerator._find_datetime_column(df)
        if not date_col:
            return None

        dates = pd.to_datetime(df[date_col], errors="coerce")
        valid = df.loc[dates.notna()].copy()
        if valid.empty:
            return None

        valid["_chart_date"] = dates.loc[dates.notna()]
        span_days = max((valid["_chart_date"].max() - valid["_chart_date"].min()).days, 0)
        if span_days > 730:
            freq = "ME"
            label = "Mese"
        elif span_days > 120:
            freq = "W"
            label = "Settimana"
        else:
            freq = "D"
            label = "Giorno"

        trend = (
            valid.set_index("_chart_date")
            .resample(freq)
            .size()
            .reset_index(name="Ticket")
        )

        fig = px.line(
            trend,
            x="_chart_date",
            y="Ticket",
            markers=True,
            title=f"Andamento lavorazione ticket per {date_col}",
            labels={"_chart_date": label, "Ticket": "Ticket"},
        )
        fig.update_layout(template="plotly_dark", height=460)
        return fig

    @staticmethod
    def _find_status_column(df: pd.DataFrame):
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
            if 1 < df[column].nunique(dropna=True) <= 50
        ]
        return low_cardinality[0] if low_cardinality else None

    @staticmethod
    def _find_datetime_column(df: pd.DataFrame):
        name_keywords = [
            "data", "date", "time", "ora", "created", "updated",
            "apertura", "chiusura", "lavorazione", "creation", "update",
        ]

        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                return column

        named_candidates = [
            column for column in df.columns
            if any(keyword in str(column).lower() for keyword in name_keywords)
        ]
        for column in named_candidates + list(df.columns):
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().sum() >= max(3, int(len(df) * 0.2)):
                return column

        return None
    
    @staticmethod
    def create_summary_dashboard(df: pd.DataFrame) -> go.Figure:
        """
        Crea una dashboard riepilogativa
        """
        try:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_cols:
                return None
            
            fig = make_subplots(
                rows=2, cols=2,
                specs=[[{'type': 'scatter'}, {'type': 'histogram'}],
                       [{'type': 'scatter'}, {'type': 'histogram'}]],
                subplot_titles=tuple(numeric_cols[:4])
            )
            
            # Popola i subplot
            for idx, col in enumerate(numeric_cols[:4]):
                row = idx // 2 + 1
                col_pos = idx % 2 + 1
                
                if idx % 2 == 0:
                    fig.add_trace(
                        go.Scatter(y=df[col], mode='lines', name=col),
                        row=row, col=col_pos
                    )
                else:
                    fig.add_trace(
                        go.Histogram(x=df[col], name=col, nbinsx=20),
                        row=row, col=col_pos
                    )
            
            fig.update_layout(
                template='plotly_dark',
                height=700,
                showlegend=False,
                title_text="📊 Dashboard Riepilogativa"
            )
            
            return fig
        except Exception as e:
            logger.error("Generazione dashboard riepilogativa fallita: %s", type(e).__name__)
            print(f"❌ Errore dashboard: {e}")
            return None
