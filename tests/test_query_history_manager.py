from utils.query_history_manager import QueryHistoryManager


def test_query_history_feedback_roundtrip():
    manager = QueryHistoryManager()
    query_id = manager.add_query(
        description="pytest feedback query",
        query_text="SELECT * FROM test",
        source_type="oracle",
        notes="pytest",
    )

    manager.update_feedback(query_id, success=True, feedback_score=0.9)
    similar = manager.find_similar_queries("pytest feedback query", "oracle", 0.9)

    row = next(item for item in similar if item["id"] == query_id)
    assert row["feedback_score"] == 0.9
    assert row["success_count"] >= 1
    assert row["execution_count"] >= 2
