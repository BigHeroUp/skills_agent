from utils.pdf_generator import PDFGenerator


def test_pdf_business_section_uses_final_report_not_raw_insights():
    generator = PDFGenerator()

    elements = generator._build_business_report_section({
        "final_report": "# Report business\n\n## Executive Summary\n- Sintesi",
        "insights": {"local_analysis": {"raw": "value"}},
    })
    rendered_text = "\n".join(
        element.getPlainText()
        for element in elements
        if hasattr(element, "getPlainText")
    )

    assert "Report business" in rendered_text
    assert "Executive Summary" in rendered_text
    assert "local_analysis" not in rendered_text
    assert "{'raw': 'value'}" not in rendered_text
