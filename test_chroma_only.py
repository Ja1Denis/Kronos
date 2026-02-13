import chromadb
import os

db_path = "data/store"
print(f"Testing ChromaDB at {os.path.abspath(db_path)}...")

try:
    client = chromadb.PersistentClient(path=db_path)
    print("Client connected.")
    
    # List collections
    collections = client.list_collections()
    print(f"Collections found: {[c.name for c in collections]}")
    
    if "kronos_memory" in [c.name for c in collections]:
        collection = client.get_collection(name="kronos_memory")
        print("Collection 'kronos_memory' retrieved.")
        print(f"Items in collection: {collection.count()}")
        
        print("Performing query...")
        res = collection.query(
            query_texts=["Što je Kronos?"],
            n_results=5
        )
        print("Query successful!")
        print(res)
    else:
        print("Collection 'kronos_memory' not found!")
        
except Exception as e:
    print(f"Encountered error: {e}")
    import traceback
    traceback.print_exc()
except BaseException as e:
    print(f"CRITICAL: {type(e)}")
