import services.analysis_service as analysis_service


def test_non_knowledge_graph_question_returns_none():
    result = analysis_service.try_run_knowledge_graph_query("mi riassumi il risultato corrente?")

    assert result is None


def test_knowledge_graph_question_activates_query_engine(monkeypatch):
    class FakeQueryEngine:
        def answer_question_deterministic(self, question):
            return {
                "question": question,
                "answer": "Ho trovato 1 funzione per grafici.",
                "matches": [
                    {
                        "id": "python_function:utils/chart_generator.py:generate_dashboard_charts",
                        "type": "python_function",
                        "label": "generate_dashboard_charts",
                        "properties": {"file": "utils/chart_generator.py", "line": 42},
                    }
                ],
                "confidence": 0.91,
                "execution_type": "deterministic_kg_query",
            }

    monkeypatch.setattr(analysis_service, "KnowledgeGraphQueryEngine", FakeQueryEngine)

    result = analysis_service.try_run_knowledge_graph_query("quali funzioni generano grafici?")

    assert result is not None
    assert result["execution_type"] == "deterministic_kg_query"
    assert result["matches"][0]["type"] == "python_function"
    assert "generate_dashboard_charts" in result["message"]
    assert "file=utils/chart_generator.py" in result["message"]


def test_missing_knowledge_graph_json_does_not_break_chat(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    result = analysis_service.try_run_knowledge_graph_query("quali funzioni generano grafici?")

    assert result is not None
    assert result["execution_type"] == "deterministic_kg_query"
    assert result["matches"] == []
    assert "Knowledge Graph non trovato" in result["message"]


def test_response_contains_deterministic_execution_type(monkeypatch):
    class FakeQueryEngine:
        def answer_question_deterministic(self, question):
            return {
                "question": question,
                "answer": "Ho trovato 1 report.",
                "matches": [{"id": "report:r1", "type": "report", "label": "final_report", "properties": {}}],
                "confidence": 0.8,
                "execution_type": "deterministic_kg_query",
            }

    monkeypatch.setattr(analysis_service, "KnowledgeGraphQueryEngine", FakeQueryEngine)

    result = analysis_service.try_run_knowledge_graph_query("quali report sono nel grafo?")

    assert result["execution_type"] == "deterministic_kg_query"
    assert "Execution type: deterministic_kg_query" in result["message"]
