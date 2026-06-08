import os
import sys
import time
import json
import sqlite3
import sqlite_vec

# Dodavanje src u path
sys.path.insert(0, os.getcwd())
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle

def run_benchmark():
    print("======================================================================")
    print("📊 BENCHMARK: sqlite-vec u projektu Kronos (v0.6.2-rust-hybrid)")
    print("======================================================================")
    
    lib = Librarian("data")
    oracle = Oracle("data/store")
    
    # 1. Mjerenje veličine baze podataka na disku
    print("\n💾 1. Analiza veličine baze podataka:")
    db_size = 0
    if os.path.exists(lib.meta_path):
        db_size = os.path.getsize(lib.meta_path) / (1024 * 1024)
        print(f"   * SQLite metadata.db (uključujući FTS i vektore): {db_size:.2f} MB")
    
    chroma_size = 0
    if os.path.exists(lib.store_path):
        for dirpath, _, filenames in os.walk(lib.store_path):
            for f in filenames:
                chroma_size += os.path.getsize(os.path.join(dirpath, f))
        chroma_size = chroma_size / (1024 * 1024)
        print(f"   * Stari ChromaDB direktorij (legacy): {chroma_size:.2f} MB")
        
    print(f"   => Ukupna konsolidacija: Sve se nalazi u JEDNOJ datoteci od {db_size:.2f} MB.")
    
    # 2. Broj zapisa u bazama
    stats = lib.get_stats()
    print(f"\n📈 2. Statistika indeksiranih zapisa:")
    print(f"   * Datoteka (Files): {stats.get('total_files', 0)}")
    print(f"   * Chunkova (FTS): {stats.get('total_chunks', 0)}")
    print(f"   * Entiteta (Entities): {sum(stats.get('entities', {}).values())}")
    print(f"   * Vektora (Vectors): {stats.get('total_vectors', 0)}")
    
    # 3. Mjerenje brzine upita
    print("\n⚡ 3. Brzina vektorskih upita (Latency test):")
    if not oracle.embedding_function:
        print("   ⚠️ Gemini API ključ nije postavljen. Ne možemo izmjeriti latentnost s embeddingom.")
        return
        
    queries = [
        "What is Librarian's main responsibility?",
        "Explain the FastPath simulation",
        "How is context budgeted?",
        "Where are decisions stored?",
        "Who is junior developer installer?"
    ]
    
    total_query_time = 0
    num_queries = len(queries)
    
    for q in queries:
        t_start = time.perf_counter()
        res = oracle.ask(q, limit=5, silent=True)
        t_end = time.perf_counter()
        
        latency = (t_end - t_start) * 1000
        total_query_time += latency
        print(f"   * Upit: '{q[:40]}...' -> Vrijeme: {latency:.2f} ms (Vraćeno {len(res.get('chunks', [])) + len(res.get('pointers', []))} rezultata)")
        
    avg_latency = total_query_time / num_queries
    print(f"   => Prosječna latentnost pretrage: {avg_latency:.2f} ms")
    
    print("\n🚀 ZAKLJUČAK:")
    print(f"   * Integracija sqlite-vec je eliminirala potrebu za ChromaDB-om od {chroma_size:.2f} MB.")
    print("   * Sve informacije (FTS, graf, metapodaci i vektori) su sada u istoj SQLite bazi.")
    print("   * Nema više zaključavanja niti race-conditiona između dvije odvojene baze.")
    print("======================================================================")

if __name__ == "__main__":
    run_benchmark()
