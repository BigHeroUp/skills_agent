"""
Modulo per generazione automatica grafici
Analizza i dati e crea grafici Plotly appropriati
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Any
from utils.logging_config import get_logger


logger = get_logger("charts")


class ChartGenerator:
    """Genera grafici automatici dai dati"""

    TECHNICAL_IDENTIFIER_TERMS = {
        "id",
        "pyid",
        "pzinskey",
        "uuid",
        "guid",
        "key",
        "idcontratto",
        "idcontrattotlm",
        "contrattoid",
        "contractid",
        "smartmoveid",
        "serialnumber",
        "codicefiscale",
    }
    METRIC_TERMS = {
        "amount",
        "importo",
        "tempo",
        "tempoattivazione",
        "duration",
        "durata",
        "processing",
        "volume",
        "count",
        "error",
        "rate",
        "sla",
        "score",
        "revenue",
        "cost",
    }
    DATE_TERMS = {
        "date", "data", "time", "timestamp", "created", "updated", "giorno", "mese",
        "creazione", "agg", "sottoscrizione", "attivazione", "chiusura", "apertura",
    }

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
        return ChartGenerator.generate_dashboard_charts(df, insights)["charts"]

    @staticmethod
    def generate_dashboard_charts(df: pd.DataFrame, insights: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Genera grafici utili e metadata sugli elementi esclusi."""
        charts = []
        skipped_charts = []
        business_notes = []
        
        try:
            if not isinstance(df, pd.DataFrame) or df.empty:
                return {"charts": [], "skipped_charts": [], "business_insights": []}

            profiles = {
                column: ChartGenerator._profile_column(df, column)
                for column in df.columns
            }
            charts.extend(ChartGenerator._activation_time_charts(df))
            for profile in profiles.values():
                if not profile["chart_allowed"]:
                    ChartGenerator._log_skipped_chart(profile)
                    skipped_charts.append(profile)
                    note = ChartGenerator._skip_business_note(profile)
                    if note:
                        business_notes.append(note)

            numeric_cols = [
                column for column, profile in profiles.items()
                if profile["chart_allowed"] and profile["semantic_type"] == "METRIC"
            ]
            categorical_cols = [
                column for column, profile in profiles.items()
                if profile["chart_allowed"] and profile["semantic_type"] in {"CATEGORY", "BOOLEAN"}
            ]
            date_cols = [
                column for column, profile in profiles.items()
                if profile["chart_allowed"] and profile["semantic_type"] == "DATE"
            ]
            
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
                    if not ChartGenerator._has_title(charts, fig.layout.title.text):
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
                if not ChartGenerator._has_title(charts, fig.layout.title.text):
                    charts.append(fig)
            
            # 3. Distribuzione informativa per colonna categorica
            if categorical_cols:
                col = categorical_cols[0]
                top_values = df[col].value_counts().head(10)
                fig = px.bar(
                    x=top_values.values,
                    y=top_values.index,
                    orientation='h',
                    title=f"📈 Distribuzione {col}",
                    labels={'x': 'Conteggio', 'y': col},
                    color=top_values.values,
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(
                    template='plotly_dark',
                    height=400,
                    showlegend=False
                )
                if not ChartGenerator._has_title(charts, fig.layout.title.text):
                    charts.append(fig)
            
            # 4. Serie temporale se presente colonna data
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
                    if not ChartGenerator._has_title(charts, fig.layout.title.text):
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
                if not ChartGenerator._has_title(charts, fig.layout.title.text):
                    charts.append(fig)
            
            # 6. KPI riassuntivi solo per metriche informative
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
                    title="📋 KPI metriche informative",
                    template='plotly_dark',
                    height=300
                )
                if not ChartGenerator._has_title(charts, fig.layout.title.text):
                    charts.append(fig)
            
        except Exception as e:
            logger.error("Generazione grafici fallita: %s", type(e).__name__)
            print(f"⚠️ Errore generazione grafici: {e}")
        
        return {
            "charts": charts,
            "skipped_charts": skipped_charts,
            "business_insights": business_notes,
        }

    @staticmethod
    def _profile_column(df: pd.DataFrame, column) -> Dict[str, Any]:
        series = df[column]
        non_null = series.dropna()
        distinct_count = int(non_null.nunique(dropna=True))
        row_count = max(1, int(len(df)))
        dominant_ratio = 0.0
        dominant_value = None
        if not non_null.empty:
            counts = non_null.astype(str).value_counts(dropna=False)
            dominant_value = counts.index[0]
            dominant_ratio = float(counts.iloc[0]) / row_count

        semantic_type = ChartGenerator._semantic_type(column, series, distinct_count, row_count)
        reason = ""
        chart_allowed = True

        if semantic_type == "IDENTIFIER":
            chart_allowed = False
            reason = "identifier"
        elif semantic_type == "CODE" and (distinct_count > 30 or distinct_count / row_count > 0.5):
            chart_allowed = False
            reason = "technical_code_high_cardinality"
        elif distinct_count <= 1:
            chart_allowed = False
            reason = "constant"
        elif dominant_ratio > 0.95:
            chart_allowed = False
            reason = "quasi_constant"
        elif semantic_type == "BOOLEAN" and dominant_ratio > 0.95:
            chart_allowed = False
            reason = "boolean_quasi_constant"
        elif semantic_type == "CATEGORY" and (distinct_count < 2 or distinct_count > min(50, max(10, int(row_count * 0.5)))):
            chart_allowed = False
            reason = "category_not_informative"
        elif semantic_type in {"TEXT", "UNKNOWN"}:
            chart_allowed = False
            reason = "unsupported_semantic_type"

        return {
            "column": str(column),
            "semantic_type": semantic_type,
            "chart_allowed": chart_allowed,
            "reason": reason,
            "distinct_count": distinct_count,
            "dominant_ratio": round(dominant_ratio, 4),
            "dominant_value": str(dominant_value) if dominant_value is not None else None,
            "missing_count": int(series.isna().sum()),
            "duplicate_count": int(non_null.duplicated().sum()) if not non_null.empty else 0,
        }

    @staticmethod
    def _activation_time_charts(df: pd.DataFrame) -> list[go.Figure]:
        metric = "TEMPO_ATTIVAZIONE_GIORNI"
        if metric not in df.columns:
            return []
        charts: list[go.Figure] = []
        valid = df[pd.to_numeric(df[metric], errors="coerce").notna()].copy()
        if valid.empty:
            return charts
        valid[metric] = pd.to_numeric(valid[metric], errors="coerce")

        hist = px.histogram(
            valid,
            x=metric,
            nbins=30,
            title="Distribuzione tempi di attivazione",
            labels={metric: "Tempo attivazione (giorni)"},
        )
        hist.update_layout(template="plotly_dark", height=420)
        charts.append(hist)

        box = px.box(
            valid,
            y=metric,
            points="outliers",
            title="Boxplot tempi di attivazione",
            labels={metric: "Tempo attivazione (giorni)"},
        )
        box.update_layout(template="plotly_dark", height=420)
        charts.append(box)

        date_col = ChartGenerator._find_activation_date_column(valid)
        if date_col:
            parsed = pd.to_datetime(valid[date_col], errors="coerce")
            trend_df = valid.loc[parsed.notna(), [metric]].copy()
            trend_df["_activation_date"] = parsed.loc[parsed.notna()]
            trend = (
                trend_df.set_index("_activation_date")[metric]
                .resample("W")
                .agg(["mean", "median"])
                .dropna(how="all")
                .reset_index()
            )
            if not trend.empty:
                line = px.line(
                    trend,
                    x="_activation_date",
                    y=["mean", "median"],
                    markers=True,
                    title=f"Trend medio/mediano tempi attivazione per {date_col}",
                    labels={"_activation_date": "Periodo", "value": "Giorni", "variable": "Metrica"},
                )
                line.update_layout(template="plotly_dark", height=420)
                charts.append(line)

        method_col = ChartGenerator._find_method_column(valid)
        if method_col and valid[method_col].nunique(dropna=True) >= 2:
            by_method = px.box(
                valid,
                x=method_col,
                y=metric,
                points=False,
                title=f"Tempi di attivazione per {method_col}",
                labels={metric: "Tempo attivazione (giorni)", method_col: method_col},
            )
            by_method.update_layout(template="plotly_dark", height=420, xaxis_tickangle=-25)
            charts.append(by_method)
        return charts

    @staticmethod
    def _find_activation_date_column(df: pd.DataFrame):
        for preferred in ("DATASOTTOSCRIZIONE", "DATA_SOTTOSCRIZIONE", "CREAZIONE_ANTENNA"):
            if preferred in df.columns:
                return preferred
        return ChartGenerator._find_datetime_column(df)

    @staticmethod
    def _find_method_column(df: pd.DataFrame):
        for column in df.columns:
            normalized = ChartGenerator._normalize_column(column)
            if "metodoconsegna" in normalized or ("metodo" in normalized and "consegna" in normalized):
                return column
        return None

    @staticmethod
    def _has_title(charts: list[go.Figure], title: str | None) -> bool:
        if not title:
            return False
        return any(getattr(chart.layout.title, "text", None) == title for chart in charts)

    @staticmethod
    def _semantic_type(column, series: pd.Series, distinct_count: int, row_count: int) -> str:
        normalized = ChartGenerator._normalize_column(column)
        if normalized in ChartGenerator.TECHNICAL_IDENTIFIER_TERMS or any(
            term in normalized for term in ChartGenerator.TECHNICAL_IDENTIFIER_TERMS
        ):
            return "IDENTIFIER"
        if any(term in normalized for term in ChartGenerator.METRIC_TERMS):
            return "METRIC"
        if any(term in normalized for term in ChartGenerator.DATE_TERMS):
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().sum() >= max(2, int(row_count * 0.3)):
                return "DATE"
        if pd.api.types.is_bool_dtype(series):
            return "BOOLEAN"
        values = {str(value).strip().lower() for value in series.dropna().unique()[:5]}
        if values and values.issubset({"true", "false", "0", "1", "yes", "no", "si", "sì"}):
            return "BOOLEAN"
        if pd.api.types.is_numeric_dtype(series):
            unique_ratio = distinct_count / max(1, row_count)
            if unique_ratio > 0.9 and row_count >= 10:
                return "IDENTIFIER"
            return "METRIC"
        if any(term in normalized for term in {"code", "codice", "cod", "key"}):
            return "CODE"
        if 2 <= distinct_count <= min(50, max(10, int(row_count * 0.5))):
            return "CATEGORY"
        if distinct_count > min(50, max(10, int(row_count * 0.5))):
            return "CODE"
        return "UNKNOWN"

    @staticmethod
    def _normalize_column(column) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(column).lower())

    @staticmethod
    def _log_skipped_chart(profile: Dict[str, Any]):
        logger.info(
            "Chart skipped column=%s semantic_type=%s reason=%s distinct_count=%s dominant_ratio=%s",
            profile["column"],
            profile["semantic_type"],
            profile["reason"],
            profile["distinct_count"],
            profile["dominant_ratio"],
        )

    @staticmethod
    def _skip_business_note(profile: Dict[str, Any]) -> str:
        column = profile["column"]
        semantic_type = profile["semantic_type"]
        reason = profile["reason"]
        if reason in {"constant", "quasi_constant", "boolean_quasi_constant"}:
            return (
                f"{column} è quasi costante: valore prevalente {profile['dominant_value']} "
                f"nel {profile['dominant_ratio'] * 100:.1f}% dei record. "
                "Non è stata generata una distribuzione grafica perché poco informativa."
            )
        if semantic_type == "IDENTIFIER":
            return (
                f"{column} è stato riconosciuto come identificativo: escluse statistiche numeriche, "
                "top 10, istogrammi e boxplot."
            )
        if reason == "technical_code_high_cardinality":
            return f"{column} è un codice tecnico ad alta cardinalità: escluso dai grafici automatici."
        return ""

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
