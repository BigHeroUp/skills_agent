from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore


def test_store_upserts_nodes_edges_and_reloads_snapshot(tmp_path):
    path = tmp_path / "knowledge_graph.json"
    store = KnowledgeGraphStore(path)

    store.upsert_node(KnowledgeNode("node:1", "dataset", "Dataset", {"rows": 10}))
    store.upsert_node(KnowledgeNode("node:1", "dataset", "Dataset aggiornato", {"rows": 20}))
    store.upsert_node(KnowledgeNode("node:2", "report", "Report"))
    store.upsert_edge(KnowledgeEdge("node:1", "node:2", "GENERATED_REPORT", {"source": "test"}))
    store.upsert_edge(KnowledgeEdge("node:1", "node:2", "GENERATED_REPORT", {"source": "updated"}))

    saved = store.save()
    reloaded = KnowledgeGraphStore(path).load()

    assert len(saved.nodes) == 2
    assert len(saved.edges) == 1
    assert len(reloaded.nodes) == 2
    assert reloaded.nodes[0].properties["rows"] == 20
    assert reloaded.edges[0].properties["source"] == "updated"


def test_store_clear_removes_json_file(tmp_path):
    path = tmp_path / "knowledge_graph.json"
    store = KnowledgeGraphStore(path)
    store.upsert_node(KnowledgeNode("node:1", "dataset", "Dataset"))
    store.save()

    store.clear()

    assert store.get_snapshot().nodes == []
    assert store.get_snapshot().edges == []
    assert not path.exists()
