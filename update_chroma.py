import chromadb
import os

db_path = "data/store"
client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(name="kronos_memory")

def get_project(path):
    if not path: return "default"
    if "MatematikaPro" in path:
        return "matematikapro"
    elif "kronos" in path.lower():
        return "kronos"
    return "default"

print("Dohvaćam sve dokumente iz ChromaDB...")
results = collection.get()

ids = results['ids']
metadatas = results['metadatas']

if not ids:
    print("Nema dokumenata u ChromaDB.")
    exit()

new_metadatas = []
for meta in metadatas:
    source = meta.get('source', '')
    meta['project'] = get_project(source)
    new_metadatas.append(meta)

print(f"Ažuriram {len(ids)} dokumenata s project tagovima...")
collection.update(
    ids=ids,
    metadatas=new_metadatas
)

print("ChromaDB ažuriran!")
