#!/usr/bin/env python3
"""
Test di integrazione locale.

Verifica i componenti principali senza richiedere database Oracle reale e senza
forzare chiamate OpenAI: il QuerySuggestionAgent viene testato sul riuso dello
storico, quindi non deve generare una nuova query con LLM.
"""

import sys
from pathlib import Path

import pandas as pd


project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_coordinator_pipeline():
    """Verifica che la pipeline contenga gli agenti attesi nell'ordine corretto."""
    from coordinator import Coordinator

    coordinator = Coordinator()
    agent_names = [agent.name for agent in coordinator.agents]

    expected = [
        "DataSourceManager",
        "QuerySuggestion",
        "DataExtractor",
        "DataValidator",
        "DataProcessor",
        "Analyst",
        "ReportGenerator",
    ]

    assert agent_names == expected, f"Pipeline inattesa: {agent_names}"
    print("OK coordinator pipeline")


def test_query_suggestion_history_reuse():
    """Verifica il riuso di una query simile gia presente nello storico."""
    import uuid

    from agents.query_suggestion_agent import QuerySuggestionAgent
    from utils.context import AgentContext
    from utils.query_history_manager import QueryHistoryManager

    token = f"integration-{uuid.uuid4().hex[:8]}"
    description = f"Analizza vendite per categoria {token}"
    query_text = f"SELECT categoria, SUM(vendite) AS totale FROM vendite /* {token} */ GROUP BY categoria"

    manager = QueryHistoryManager()
    query_id = manager.add_query(
        description=description,
        query_text=query_text,
        source_type="csv",
        notes="Test integrazione history reuse",
    )
    manager.update_feedback(query_id, success=True, feedback_score=0.95)

    context = AgentContext(user_input=description)
    context.metadata = {"source_type": "csv"}
    context.raw_data = {
        "dataframe": pd.DataFrame({
            "categoria": ["A", "B", "A"],
            "vendite": [10, 20, 5],
        }),
        "source": "csv",
    }

    agent = QuerySuggestionAgent()
    context = agent.process(context)

    suggestion = context.raw_data.get("extraction_suggestion")
    assert suggestion, "extraction_suggestion mancante"
    assert suggestion["source"] == "history"
    assert suggestion["query_id"] == query_id
    assert token in suggestion["query"]
    print("OK query suggestion history reuse")


def test_feedback_update():
    """Verifica aggiornamento feedback nello storico query."""
    import uuid

    from utils.query_history_manager import QueryHistoryManager

    description = f"Feedback integration test {uuid.uuid4().hex[:8]}"
    manager = QueryHistoryManager()
    query_id = manager.add_query(
        description=description,
        query_text="SELECT * FROM test",
        source_type="oracle",
        notes="Test feedback",
    )

    manager.update_feedback(query_id, success=False, feedback_score=0.15)
    similar = manager.find_similar_queries(description, "oracle", similarity_threshold=1.0)
    row = next((item for item in similar if item["id"] == query_id), None)

    assert row is not None, "Query aggiornata non trovata"
    assert row["execution_count"] >= 2
    assert row["feedback_score"] == 0.15
    print("OK feedback update")


def test_deterministic_analysis():
    """Verifica calcoli deterministici pandas usati dalla pipeline."""
    from utils.data_analysis import summarize_dataframe, build_deterministic_insights

    df = pd.DataFrame({
        "categoria": ["A", "A", "B", None],
        "vendite": [10, 15, 7, 20],
        "costo": [5, 8, 3, 12],
    })

    summary = summarize_dataframe(df)
    insights = build_deterministic_insights(summary)

    assert summary["row_count"] == 4
    assert summary["numeric_summary"]["vendite"]["sum"] == 52
    assert "categoria" in summary["missing_values"]
    assert insights["key_metrics"]["vendite"]["mean"] == 13
    print("OK deterministic analysis")


def main():
    print("\nINTEGRATION TEST SUITE\n")

    tests = [
        test_coordinator_pipeline,
        test_query_suggestion_history_reuse,
        test_feedback_update,
        test_deterministic_analysis,
    ]

    for test in tests:
        test()

    print("\nALL INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    main()
