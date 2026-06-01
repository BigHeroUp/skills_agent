#!/usr/bin/env python3
"""
Test script per validare i nuovi moduli
"""
import sys
from pathlib import Path

# Aggiungi il path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test imports dei nuovi moduli"""
    try:
        print("Testing QueryHistoryManager...")
        from utils.query_history_manager import QueryHistoryManager
        print("OK QueryHistoryManager imported successfully")
        
        print("\nTesting QuerySuggestionAgent...")
        from agents.query_suggestion_agent import QuerySuggestionAgent
        print("OK QuerySuggestionAgent imported successfully")
        
        print("\nTesting Coordinator...")
        from coordinator import Coordinator
        print("OK Coordinator imported successfully")
        
        print("\n" + "="*50)
        print("OK ALL IMPORTS OK")
        print("="*50)
        return True
    except Exception as e:
        print(f"ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_history_manager():
    """Test basic QueryHistoryManager functionality"""
    try:
        print("\n" + "="*50)
        print("Testing QueryHistoryManager functionality...")
        print("="*50)
        
        from utils.query_history_manager import QueryHistoryManager
        
        # Crea istanza
        manager = QueryHistoryManager()
        print("OK QueryHistoryManager instance created")
        
        # Test add query
        query_id = manager.add_query(
            description="Test query for learning",
            query_text="SELECT * FROM test",
            source_type="oracle",
            notes="Test query"
        )
        print(f"OK Query added with ID: {query_id}")
        
        # Test find similar
        similar = manager.find_similar_queries("Test query learning", "oracle", 0.5)
        print(f"OK Found {len(similar)} similar queries")
        
        # Test feedback
        manager.update_feedback(query_id, success=True, feedback_score=0.95)
        print(f"OK Feedback updated for query {query_id}")
        
        # Test get top queries
        top = manager.get_top_queries("oracle", limit=3)
        print(f"OK Retrieved top {len(top)} queries")
        
        print("\nOK QueryHistoryManager tests passed!")
        return True
    except Exception as e:
        print(f"QueryHistoryManager test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_analysis():
    """Test deterministic dataframe analysis utilities."""
    try:
        print("\n" + "="*50)
        print("Testing deterministic dataframe analysis...")
        print("="*50)

        import pandas as pd
        from utils.data_analysis import summarize_dataframe, build_deterministic_insights

        df = pd.DataFrame({
            "categoria": ["A", "A", "B", None],
            "vendite": [10, 15, 7, 20],
            "costo": [5, 8, 3, 12],
        })

        summary = summarize_dataframe(df)
        assert summary["row_count"] == 4
        assert summary["column_count"] == 3
        assert "vendite" in summary["numeric_summary"]
        assert "categoria" in summary["missing_values"]

        insights = build_deterministic_insights(summary)
        assert insights["key_metrics"]["vendite"]["sum"] == 52

        print("OK deterministic analysis tests passed")
        return True
    except Exception as e:
        print(f"Data analysis test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_skill_files():
    """Verify skill files required by agents exist."""
    try:
        print("\n" + "="*50)
        print("Testing required skill files...")
        print("="*50)

        required = [
            Path("skills/data_validation/SKILL.md"),
            Path("skills/data_processing/SKILL.md"),
            Path("skills/analysis/SKILL.md"),
            Path("skills/query_suggestion/SKILL.md"),
        ]
        missing = [str(path) for path in required if not path.exists()]
        assert not missing, f"Missing skill files: {missing}"

        print("OK required skill files exist")
        return True
    except Exception as e:
        print(f"Skill file test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_skill_prompt_builder():
    """Verify agents can compose task prompts with their SKILL.md content."""
    try:
        print("\n" + "="*50)
        print("Testing skill prompt builder...")
        print("="*50)

        from agents.query_suggestion_agent import QuerySuggestionAgent

        agent = QuerySuggestionAgent()
        prompt = agent.build_prompt_with_skill("Genera un suggerimento di test.")

        assert "ISTRUZIONI SKILL (query_suggestion)" in prompt
        assert "Query Suggestion Skill" in prompt
        assert "TASK CORRENTE" in prompt
        assert "Genera un suggerimento di test." in prompt

        print("OK skill prompt builder")
        return True
    except Exception as e:
        print(f"Skill prompt builder test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nTESTING NEW MODULES\n")
    
    success = True
    success = test_imports() and success
    success = test_history_manager() and success
    success = test_data_analysis() and success
    success = test_skill_files() and success
    success = test_skill_prompt_builder() and success
    
    if success:
        print("\n" + "="*50)
        print("ALL TESTS PASSED!")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("SOME TESTS FAILED")
        print("="*50)
        sys.exit(1)
