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
