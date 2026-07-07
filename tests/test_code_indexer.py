from services.knowledge_graph.code_indexer import PythonCodeIndexer
from services.knowledge_graph.store import KnowledgeGraphStore


def test_code_indexer_creates_python_nodes_and_relationships(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        "\n".join([
            "import os",
            "from pathlib import Path",
            "",
            "class Example:",
            "    def method(self):",
            "        return Path(os.getcwd())",
            "",
            "def top_level():",
            "    return Example()",
        ]),
        encoding="utf-8",
    )
    ignored = tmp_path / ".venv" / "ignored.py"
    ignored.parent.mkdir()
    ignored.write_text("class Ignored: pass", encoding="utf-8")

    store = KnowledgeGraphStore(tmp_path / "kg.json")
    snapshot = PythonCodeIndexer(tmp_path).index_repository(store)

    node_ids = {node.id for node in snapshot.nodes}
    edge_types = {(edge.source, edge.target, edge.relationship) for edge in snapshot.edges}

    assert "python_file:sample.py" in node_ids
    assert "python_class:sample.py:Example" in node_ids
    assert "python_function:sample.py:Example.method" in node_ids
    assert "python_function:sample.py:top_level" in node_ids
    assert "python_import:os" in node_ids
    assert "python_import:pathlib.Path" in node_ids
    assert "python_class:.venv/ignored.py:Ignored" not in node_ids
    assert ("python_file:sample.py", "python_class:sample.py:Example", "CONTAINS") in edge_types
    assert ("python_file:sample.py", "python_import:os", "IMPORTS") in edge_types
