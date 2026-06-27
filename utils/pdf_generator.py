"""
Modulo per generazione di report PDF professionali
Include grafici, analisi LLM e statistiche
"""

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, KeepTogether
)
from reportlab.lib import colors
import plotly.io as pio
from utils.logging_config import get_logger


logger = get_logger("pdf_generator")


class PDFGenerator:
    """Generatore di report PDF con grafici e analisi"""
    
    # Colori tema
    COLORS = {
        "primary": HexColor("#1f77b4"),
        "secondary": HexColor("#ff7f0e"),
        "success": HexColor("#2ca02c"),
        "danger": HexColor("#d62728"),
        "dark": HexColor("#1a1a1a"),
        "light": HexColor("#f8f9fa"),
    }
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura stili personalizzati"""
        # Titolo report
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLORS["primary"],
            spaceAfter=12,
            alignment=1  # Center
        ))
        
        # Sottotitolo
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.COLORS["dark"],
            spaceAfter=6,
            alignment=1  # Center
        ))
        
        # Sezione heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.COLORS["primary"],
            spaceAfter=10,
            spaceBefore=10
        ))
        
        # Testo insight
        self.styles.add(ParagraphStyle(
            name='Insight',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLORS["dark"],
            spaceAfter=8,
            leftIndent=20
        ))
    
    def generate_report(
        self,
        output_path: str,
        user_input: str,
        context: Dict[str, Any],
        charts_figures: List[Any] = None,
        title: str = "Multi-Agent Data Analysis Report",
    ) -> bool:
        """
        Genera un report PDF completo
        
        Args:
            output_path: Path dove salvare il PDF
            user_input: Descrizione originale dell'analisi
            context: Context con insights e processed_data
            charts_figures: Lista di figure Plotly
            title: Titolo del report
        
        Returns:
            True se generato con successo
        """
        try:
            logger.info(f"Inizio generazione PDF: {output_path}")
            
            # Assicura directory esista
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Crea documento
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            # Costruisce gli elementi del documento
            elements = self._build_pdf_content(
                user_input,
                context,
                charts_figures,
                title
            )
            
            # Genera PDF
            doc.build(elements)
            logger.info(f"PDF generato con successo: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Errore generazione PDF: {str(e)}")
            return False
    
    def _build_pdf_content(
        self,
        user_input: str,
        context: Dict[str, Any],
        charts_figures: List[Any],
        title: str
    ) -> List:
        """Costruisce il contenuto del PDF"""
        elements = []
        
        # Header
        elements.extend(self._build_header(title, user_input))
        elements.append(Spacer(1, 0.3*inch))
        
        elements.extend(self._build_business_report_section(context))
        elements.append(Spacer(1, 0.3*inch))
        
        # Grafici
        if charts_figures:
            elements.append(PageBreak())
            elements.extend(self._build_charts_section(charts_figures))
            elements.append(Spacer(1, 0.2*inch))
        
        # Footer
        elements.extend(self._build_footer())
        
        return elements
    
    def _build_header(self, title: str, user_input: str) -> List:
        """Costruisce header del documento"""
        elements = []
        
        elements.append(
            Paragraph(title, self.styles['ReportTitle'])
        )
        
        elements.append(
            Paragraph("Data Analysis Report", self.styles['ReportSubtitle'])
        )
        
        elements.append(
            Paragraph(
                f"<b>Richiesta:</b> {user_input[:100]}{'...' if len(user_input) > 100 else ''}",
                self.styles['Normal']
            )
        )
        
        elements.append(
            Paragraph(
                f"<b>Generato:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                self.styles['Normal']
            )
        )
        
        return elements
    
    def _build_summary(self, context: Dict[str, Any]) -> List:
        """Crea sezione summary"""
        elements = []
        
        elements.append(
            Paragraph("Executive Summary", self.styles['SectionHeading'])
        )
        
        summary_text = context.get('final_report', 'Analisi completata senza report.')
        if len(summary_text) > 500:
            summary_text = summary_text[:500] + "..."
        
        elements.append(
            Paragraph(summary_text, self.styles['Normal'])
        )
        
        return elements

    def _build_business_report_section(self, context: Dict[str, Any]) -> List:
        """Renderizza il report business senza dump tecnici raw."""
        final_report = context.get('final_report') or context.get('insights', {}).get('local_final_report')
        if not final_report:
            final_report = "Analisi completata senza report business disponibile."
        return self._markdown_to_flowables(str(final_report))

    def _markdown_to_flowables(self, markdown_text: str) -> List:
        elements = []
        table_rows = []

        def flush_table():
            nonlocal table_rows
            if not table_rows:
                return
            cleaned_rows = [
                [self._clean_inline_markdown(cell.strip()) for cell in row]
                for row in table_rows
                if row and not all(re.fullmatch(r"-+", cell.strip()) for cell in row)
            ]
            table_rows = []
            if not cleaned_rows:
                return
            table = Table(cleaned_rows, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light']),
                ('TEXTCOLOR', (0, 1), (-1, -1), self.COLORS['dark']),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.12*inch))

        for raw_line in markdown_text.splitlines():
            line = raw_line.strip()
            if not line:
                flush_table()
                elements.append(Spacer(1, 0.08*inch))
                continue
            if line.startswith("|") and line.endswith("|"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    table_rows.append(cells)
                continue
            flush_table()
            if line.startswith("# "):
                elements.append(Paragraph(self._clean_inline_markdown(line[2:]), self.styles['ReportTitle']))
            elif line.startswith("## "):
                elements.append(Paragraph(self._clean_inline_markdown(line[3:]), self.styles['SectionHeading']))
            elif line.startswith("- "):
                elements.append(Paragraph(f"• {self._clean_inline_markdown(line[2:])}", self.styles['Insight']))
            elif re.match(r"^\d+\. ", line):
                elements.append(Paragraph(self._clean_inline_markdown(line), self.styles['Insight']))
            else:
                elements.append(Paragraph(self._clean_inline_markdown(line), self.styles['Normal']))
        flush_table()
        return elements

    def _clean_inline_markdown(self, value: str) -> str:
        text = escape(str(value))
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        return text
    
    def _build_charts_section(self, charts_figures: List[Any]) -> List:
        """Crea sezione grafici"""
        elements = []
        
        elements.append(
            Paragraph("Visualizzazioni dati", self.styles['SectionHeading'])
        )
        
        for i, fig in enumerate(charts_figures, 1):
            try:
                # Converte Plotly figure in immagine PNG
                img_bytes = pio.to_image(fig, format="png", width=600, height=400)
                img = Image(io.BytesIO(img_bytes), width=6*inch, height=4*inch)
                
                elements.append(img)
                elements.append(Spacer(1, 0.2*inch))
                
                # Aggiunge titolo grafico se disponibile
                if hasattr(fig, 'layout') and hasattr(fig.layout, 'title'):
                    title = fig.layout.title.text if fig.layout.title.text else f"Grafico {i}"
                    elements.append(
                        Paragraph(f"<i>{title}</i>", self.styles['Normal'])
                    )
                    elements.append(Spacer(1, 0.15*inch))
                
            except Exception as e:
                logger.warning(f"Errore conversione grafico {i}: {str(e)}")
                elements.append(
                    Paragraph(f"Errore visualizzazione grafico {i}", self.styles['Normal'])
                )
            
            if i % 2 == 0:
                elements.append(PageBreak())
        
        return elements
    
    def _build_insights_section(self, context: Dict[str, Any]) -> List:
        """Crea sezione insights"""
        elements = []
        
        elements.append(
            Paragraph("🔍 Analisi e Insight", self.styles['SectionHeading'])
        )
        
        insights = context.get('insights', {})
        if not insights:
            elements.append(
                Paragraph("Nessun insight disponibile", self.styles['Normal'])
            )
            return elements
        
        # Formatta insights per PDF
        if isinstance(insights, dict):
            allowed_keys = (
                "executive_summary",
                "key_findings",
                "data_quality_notes",
                "operational_recommendations",
                "openai_enrichment",
                "openai_report_enrichment",
            )
            for key in allowed_keys:
                value = insights.get(key)
                if not value:
                    continue
                if isinstance(value, str):
                    elements.append(
                        Paragraph(f"<b>• {escape(key)}:</b> {self._clean_inline_markdown(value)}", self.styles['Insight'])
                    )
                elif isinstance(value, list):
                    summary = "; ".join(str(item) for item in value[:5])
                    elements.append(
                        Paragraph(f"<b>• {escape(key)}:</b> {self._clean_inline_markdown(summary)}", self.styles['Insight'])
                    )
        else:
            elements.append(Paragraph(self._clean_inline_markdown(str(insights)[:500]), self.styles['Normal']))
        
        return elements
    
    def _build_statistics_section(self, context: Dict[str, Any]) -> List:
        """Crea sezione statistiche"""
        elements = []
        
        elements.append(
            Paragraph("📈 Statistiche", self.styles['SectionHeading'])
        )
        
        raw_data = context.get('raw_data', {})
        processed_data = context.get('processed_data', {})
        
        # Crea tabella statistiche
        stats_data = [
            ["Metrica", "Valore"],
            ["Righe Elaborate", str(raw_data.get('row_count', 'N/A'))],
            ["Colonne", str(len(raw_data.get('columns', [])))],
            ["Data Validazione", "✅ Valida" if context.get('is_valid') else "❌ Non valida"],
            ["Errori Accumulati", str(len(context.get('errors', [])))],
        ]
        
        table = Table(stats_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light']),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_footer(self) -> List:
        """Crea footer del documento"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        
        footer_text = "Multi-Agent Data Analysis Platform | Report generato automaticamente"
        elements.append(
            Paragraph(footer_text, self.styles['Normal'])
        )
        
        return elements
