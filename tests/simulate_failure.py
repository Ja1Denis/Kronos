import sys
import os
import chromadb
from tenacity import RetryError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.modules.oracle import resilient_vector_query
from src.utils.metrics import metrics

def simulate_failure():
    print("🧪 Simulating ChromaDB failure (invalid collection)...")
    client = chromadb.PersistentClient(path="data/store")
    # Simuliramo i upit kako bi health score pao
    metrics.log_query()
    try:
        # resilient_vector_query prima (collection, query, n_results, where)
        resilient_vector_query(None, "test query") 
    except Exception:
        pass
    
    print(f"📊 Current failure metrics: {metrics.vector_failures}")
    print(f"📈 Total queries: {metrics.total_queries}")
    print(f"🏥 Health score: {metrics.health_score()}%")

if __name__ == "__main__":
    simulate_failure()
