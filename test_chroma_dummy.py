import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
import os

class MyDummyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        # Return dummy embeddings (zeros)
        return [[0.1] * 384 for _ in range(len(input))]

db_path = "data/store"
print(f"Testing ChromaDB with Dummy Embeddings at {os.path.abspath(db_path)}...")

try:
    client = chromadb.PersistentClient(path=db_path)
    print("Client connected.")
    
    # Use dummy embedding function to avoid loading heavy models
    emb_fn = MyDummyEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name="kronos_memory", 
        embedding_function=emb_fn
    )
    print(f"Collection retrieved. Count: {collection.count()}")
    
    print("Performing query with dummy embeddings...")
    res = collection.query(
        query_texts=["Što je Kronos?"],
        n_results=5
    )
    print("Query successful!")
    print(res)
        
except Exception as e:
    print(f"Encountered error: {e}")
    import traceback
    traceback.print_exc()
except BaseException as e:
    print(f"CRITICAL PAD: {type(e)}")
