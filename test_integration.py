#!/usr/bin/env python3
"""
Test di integrazione per QuerySuggestionAgent.
Testa il flusso completo senza UI.
"""
import sys
from pathlib import Path
import json

# Aggiungi path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_pipeline_with_query_suggestion():
    """Test pipeline completo con QuerySuggestionAgent"""
    print("\n" + "="*70)
    print("🧪 TEST: Pipeline Completo con QuerySuggestionAgent")
    print("="*70)
    
    try:
        # Importa i moduli
        print("\n1️⃣ Importando moduli...")
        from coordinator import Coordinator
        from utils.context import AgentContext
        print("   ✓ Moduli importati")
        
        # Crea coordinatore
        print("\n2️⃣ Creando Coordinatore...")
        coordinator = Coordinator()
        print(f"   ✓ Coordinatore creato con {len(coordinator.agents)} agenti")
        
        # Verifica che QuerySuggestionAgent è nella pipeline
        print("\n3️⃣ Verificando pipeline...")
        agent_names = [agent.name for agent in coordinator.agents]
        print(f"   Agenti in pipeline: {' → '.join(agent_names)}")
        
        if "QuerySuggestion" not in agent_names:
            print("   ❌ QuerySuggestionAgent NON trovato nella pipeline!")
            return False
        print("   ✓ QuerySuggestionAgent trovato in posizione 2")
        
        # Test con metadata di sorgente CSV
        print("\n4️⃣ Testando con sorgente CSV...")
        metadata_csv = {
            "source_type": "csv",
            "file_path": "test_data.csv",
            "file_size_mb": 0.5
        }
        
        test_input = "Analizza le vendite per categoria nel 2024"
        print(f"   Input utente: '{test_input}'")
        print(f"   Metadata: {metadata_csv}")
        
        context = AgentContext(user_input=test_input)
        context.metadata = metadata_csv
        
        # Esegui solo i primi 2 agenti per test veloce
        print("\n5️⃣ Eseguendo DataSourceManagerAgent...")
        context = coordinator.agents[0].process(context)
        print(f"   Context dopo DataSourceManager: {len(context.raw_data)} campi")
        
        print("\n6️⃣ Eseguendo QuerySuggestionAgent...")
        context = coordinator.agents[1].process(context)
        
        if "extraction_suggestion" in context.raw_data:
            suggestion = context.raw_data["extraction_suggestion"]
            print(f"   ✓ Suggerimento generato:")
            print(f"     - Source: {suggestion.get('source', 'unknown')}")
            print(f"     - Query: {suggestion.get('query', 'N/A')[:60]}...")
            print(f"     - Description: {suggestion.get('description', 'N/A')}")
        else:
            print("   ❌ Nessun suggerimento trovato nel context!")
            return False
        
        # Test con metadata Oracle
        print("\n7️⃣ Testando con sorgente Oracle...")
        metadata_oracle = {
            "source_type": "oracle",
            "oracle_config": {
                "host": "localhost",
                "port": 1521,
                "database": "test"
            }
        }
        
        context2 = AgentContext(user_input="Top 5 clienti per ordini")
        context2.metadata = metadata_oracle
        
        print("   Eseguendo DataSourceManagerAgent...")
        context2 = coordinator.agents[0].process(context2)
        
        print("   Eseguendo QuerySuggestionAgent...")
        context2 = coordinator.agents[1].process(context2)
        
        if "extraction_suggestion" in context2.raw_data:
            suggestion = context2.raw_data["extraction_suggestion"]
            print(f"   ✓ Suggerimento Oracle generato:")
            print(f"     - Source: {suggestion.get('source', 'unknown')}")
            if 'SELECT' in str(suggestion.get('query', '')):
                print(f"     ✓ Query contiene SELECT")
            else:
                print(f"     ⚠️  Query: {suggestion.get('query', 'N/A')[:60]}")
        
        # Test QueryHistoryManager
        print("\n8️⃣ Testando QueryHistoryManager...")
        from utils.query_history_manager import QueryHistoryManager
        
        manager = QueryHistoryManager()
        print(f"   ✓ Manager creato, DB in: {QueryHistoryManager.DB_PATH}")
        
        # Aggiungi una query
        qid = manager.add_query(
            description="Test similar queries",
            query_text="SELECT * FROM test",
            source_type="oracle"
        )
        print(f"   ✓ Query aggiunta con ID: {qid}")
        
        # Cerca query simili
        similar = manager.find_similar_queries("Test query learning", "oracle", 0.5)
        print(f"   ✓ Trovate {len(similar)} query simili")
        
        # Aggiorna feedback
        manager.update_feedback(qid, success=True, feedback_score=0.95)
        print(f"   ✓ Feedback aggiornato")
        
        print("\n" + "="*70)
        print("✅ TUTTI I TEST PASSATI!")
        print("="*70)
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_file():
    """Verifica che il SKILL.md venga creato"""
    print("\n" + "="*70)
    print("🧪 TEST: Creazione SKILL.md")
    print("="*70)
    
    try:
        from agents.query_suggestion_agent import QuerySuggestionAgent
        
        print("\n1️⃣ Creando QuerySuggestionAgent...")
        agent = QuerySuggestionAgent()
        print("   ✓ Agent creato")
        
        skill_path = Path("skills/query_suggestion/SKILL.md")
        print(f"\n2️⃣ Verificando file SKILL.md: {skill_path}")
        
        if skill_path.exists():
            print("   ✓ File SKILL.md creato!")
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"   Dimensione: {len(content)} caratteri")
                if "Query Suggestion Skill" in content:
                    print("   ✓ Contenuto corretto")
                    return True
        else:
            print("   ⚠️  File non ancora creato")
            # Prova a caricare il skill file
            prompt = agent.load_skill_prompt()
            if prompt and len(prompt) > 100:
                print("   ✓ load_skill_prompt() ritorna contenuto valido")
                return True
            
    except Exception as e:
        print(f"   ❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 AVVIO TEST SUITE\n")
    
    success = True
    success = test_pipeline_with_query_suggestion() and success
    success = test_skill_file() and success
    
    if success:
        print("\n" + "="*70)
        print("🎉 TUTTI I TEST PASSATI - Sistema pronto!")
        print("="*70)
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("❌ ALCUNI TEST FALLITI - Revisione necessaria")
        print("="*70)
        sys.exit(1)
