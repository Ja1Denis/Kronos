from src.modules.librarian import Librarian
from src.modules.oracle import Oracle
import os

# Putanja do baze
lib = Librarian("data")
oracle = Oracle("data/store")

print("--- SQLITE STATS ---")
print(lib.get_stats())

print("\n--- FTS SEARCH (plavi slon) ---")
results = lib.search_fts("plavi slon")
print(results)

print("\n--- CHROMA SEARCH (plavi slon) ---")
# Koristimo sirovi query nad kolekcijom
res = oracle.collection.query(query_texts=["plavi slon"], n_results=1)
print(res)
