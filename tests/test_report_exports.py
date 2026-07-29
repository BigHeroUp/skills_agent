from io import BytesIO

from docx import Document
from pypdf import PdfReader

from services.report_exports import build_docx, build_pdf


REPORT = """# Sintesi esecutiva

Il risultato deriva da calcoli deterministici.

## Evidenze
- Ricavi totali: 1250
- Record analizzati: 20
"""


def test_pdf_export_is_readable_and_contains_report_text():
    content = build_pdf(REPORT, "Analisi dimostrativa")
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert content.startswith(b"%PDF")
    assert "Analisi dimostrativa" in text
    assert "Ricavi totali" in text


def test_docx_export_is_readable_and_structured():
    content = build_docx(REPORT, "Analisi dimostrativa")
    document = Document(BytesIO(content))
    text = "\n".join(item.text for item in document.paragraphs)
    assert content.startswith(b"PK")
    assert "Analisi dimostrativa" in text
    assert "Ricavi totali" in text
