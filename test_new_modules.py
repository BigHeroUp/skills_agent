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
        print("✓ QueryHistoryManager imported successfully")
        
        print("\nTesting QuerySuggestionAgent...")
        from agents.query_suggestion_agent import QuerySuggestionAgent
        print("✓ QuerySuggestionAgent imported successfully")
        
        print("\nTesting Coordinator...")
        from coordinator import Coordinator
        print("✓ Coordinator imported successfully")
        
        print("\n" + "="*50)
        print("✓ ALL IMPORTS OK")
        print("="*50)
        return True
    except Exception as e:
        print(f"✗ ERRORE: {e}")
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
        print("✓ QueryHistoryManager instance created")
        
        # Test add query
        query_id = manager.add_query(
            description="Test query for learning",
            query_text="SELECT * FROM test",
            source_type="oracle",
            notes="Test query"
        )
        print(f"✓ Query added with ID: {query_id}")
        
        # Test find similar
        similar = manager.find_similar_queries("Test query learning", "oracle", 0.5)
        print(f"✓ Found {len(similar)} similar queries")
        
        # Test feedback
        manager.update_feedback(query_id, success=True, feedback_score=0.95)
        print(f"✓ Feedback updated for query {query_id}")
        
        # Test get top queries
        top = manager.get_top_queries("oracle", limit=3)
        print(f"✓ Retrieved top {len(top)} queries")
        
        print("\n✓ QueryHistoryManager tests passed!")
        return True
    except Exception as e:
        print(f"✗ QueryHistoryManager test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 TESTING NEW MODULES\n")
    
    success = True
    success = test_imports() and success
    success = test_history_manager() and success
    
    if success:
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("❌ SOME TESTS FAILED")
        print("="*50)
        sys.exit(1)
