from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "platform_api" / "templates"


def test_primary_pages_declare_italian_language_and_viewport():
    for name in ("portal.html", "analysis_result.html", "knowledge_workspace.html", "quality_center.html", "beta_guide.html"):
        content = (TEMPLATES / name).read_text()
        assert '<html lang="it"' in content
        assert 'name="viewport"' in content


def test_tooltips_are_available_to_pointer_and_keyboard_users():
    css = (ROOT / "platform_api" / "static" / "tooltips.css").read_text()
    assert "[data-tooltip]:hover::after" in css
    assert "[data-tooltip]:focus-visible::after" in css
    for name in ("portal.html", "analysis_result.html", "knowledge_workspace.html"):
        assert "data-tooltip=" in (TEMPLATES / name).read_text()


def test_knowledge_graph_and_dynamic_messages_have_accessible_names():
    content = (TEMPLATES / "knowledge_workspace.html").read_text()
    assert 'role="img" aria-label="Grafo interattivo della conoscenza"' in content
    assert 'role="status" aria-live="polite"' in content
    assert '<label for="search">' in content
    assert 'aria-label="Cerca"' in content
