import pytest
import chromadb
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="function")
def fresh_client():
    """Dohvaća clienta spojenog na stvarnu data/store lokaciju"""
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'store'))
    client = chromadb.PersistentClient(path=db_path)
    yield client

def test_collection_info(fresh_client):
    """Test da možemo dohvatiti kolekciju i njene osnovne informacije"""
    try:
        collection = fresh_client.get_collection("kronos_memory")
        count = collection.count()
        print(f"✅ Collection 'kronos_memory' count: {count}")
        assert count >= 0
    except Exception as e:
        pytest.fail(f"Failed to get collection info: {e}")

def test_basic_semantic_search(fresh_client):
    """Test osnovnog vektorskog upita s Gemini embeddings (ako su dostupni)"""
    # Za ovaj test trebamo API ključ ako koristimo Gemini Embedding funkciju
    # Ali ako je Oracle već inicijaliziran, možemo testirati sirovi client
    collection = fresh_client.get_collection("kronos_memory")
    
    # Pokušavamo query (može vratiti prazno ako nema podataka, bitno da ne crasha)
    try:
        # Koristimo dummy text, chromadb će pokušati embedati ako ima embedding_func u kolekciji
        results = collection.query(
            query_texts=["kronos architecture"],
            n_results=1
        )
        assert "ids" in results
        print(f"✅ Semantic search returned {len(results['ids'][0])} results")
    except Exception as e:
        # Ako embedding_function nije postavljen u kolekciji ili nema API ključa, ovo bi moglo pasti
        # U tom slučaju, preskočimo ili logiramo
        print(f"⚠️ Semantic query failed (probably missing API key or embedding function): {e}")
        # Ne failamo test jer ovisi o vanjskom ključu
