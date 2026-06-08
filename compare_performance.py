import os
import sys
import time
import sqlite3
import sqlite_vec
import chromadb
from chromadb.utils import embedding_functions

# Dodaj src u path
sys.path.insert(0, os.getcwd())

def run_comparison():
    print("======================================================================")
    print("🚀 USPOREDNI TEST PERFORMANSI: ChromaDB vs sqlite-vec")
    print("======================================================================")
    
    # 1. Priprema API ključa za embeddings
    from dotenv import load_dotenv
    load_dotenv(os.path.join("..", ".agent", ".env"))
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Greška: GEMINI_API_KEY nije postavljen u .env datoteci.")
        return
        
    # Inicijalizacija embedding funkcije
    emb_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
        api_key=api_key,
        model_name="models/gemini-embedding-001"
    )
    
    query_text = "What is the architecture of Kronos?"
    print(f"Generating query embedding for: '{query_text}'...")
    query_vector = emb_fn([query_text])[0]
    
    # ----------------------------------------------------
    # CHROMADB USPOREDBA (LEGACY)
    # ----------------------------------------------------
    print("\n⏱️ 1. Testiranje ChromaDB (Legacy)...")
    chroma_store = "data/store"
    
    if not os.path.exists(chroma_store):
        print("⚠️ Upozorenje: ChromaDB direktorij 'data/store' nije pronađen. Koristim privremeni.")
        
    try:
        t_start_init = time.perf_counter()
        chroma_client = chromadb.PersistentClient(path=chroma_store)
        chroma_collection = chroma_client.get_or_create_collection(
            name="kronos_memory",
            embedding_function=emb_fn
        )
        t_end_init = time.perf_counter()
        chroma_init_ms = (t_end_init - t_start_init) * 1000
        print(f"   * Vrijeme inicijalizacije ChromaDB klijenta: {chroma_init_ms:.2f} ms")
        
        # Mjerenje query brzine (10 iteracija)
        chroma_query_times = []
        for i in range(10):
            t_start = time.perf_counter()
            # Radimo pretragu s generiranim vektorom da izbjegnemo ponovno pozivanje API-ja
            results = chroma_collection.query(
                query_embeddings=[query_vector],
                n_results=5
            )
            t_end = time.perf_counter()
            chroma_query_times.append((t_end - t_start) * 1000)
            
        avg_chroma_query = sum(chroma_query_times) / len(chroma_query_times)
        print(f"   * Prosječno vrijeme pretrage (ChromaDB): {avg_chroma_query:.2f} ms")
    except Exception as e:
        print(f"   ❌ ChromaDB test nije uspio: {e}")
        avg_chroma_query = None
        chroma_init_ms = None

    # ----------------------------------------------------
    # SQLITE-VEC USPOREDBA (NEW)
    # ----------------------------------------------------
    print("\n⏱️ 2. Testiranje sqlite-vec (Novo)...")
    db_path = "data/metadata.db"
    
    try:
        t_start_init = time.perf_counter()
        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        t_end_init = time.perf_counter()
        sqlite_init_ms = (t_end_init - t_start_init) * 1000
        print(f"   * Vrijeme inicijalizacije SQLite + sqlite-vec: {sqlite_init_ms:.2f} ms")
        
        # Priprema bajtova za sqlite-vec
        emb_bytes = sqlite_vec.serialize_float32(query_vector)
        
        # Mjerenje query brzine (10 iteracija)
        sqlite_query_times = []
        for i in range(10):
            t_start = time.perf_counter()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.custom_id, m.document, v.distance
                FROM vec_items v
                JOIN vec_metadata m ON v.rowid = m.rowid
                WHERE v.embedding MATCH ? AND k = 5
                ORDER BY v.distance ASC
            ''', (emb_bytes,))
            results = cursor.fetchall()
            t_end = time.perf_counter()
            sqlite_query_times.append((t_end - t_start) * 1000)
            
        avg_sqlite_query = sum(sqlite_query_times) / len(sqlite_query_times)
        print(f"   * Prosječno vrijeme pretrage (sqlite-vec): {avg_sqlite_query:.2f} ms")
        conn.close()
    except Exception as e:
        print(f"   ❌ sqlite-vec test nije uspio: {e}")
        avg_sqlite_query = None
        sqlite_init_ms = None

    # ----------------------------------------------------
    # REZULTAT
    # ----------------------------------------------------
    print("\n======================================================================")
    print("📊 USPOREDNA TABLICA PERFORMANSI")
    print("======================================================================")
    print(f"{'Metrika':<35} | {'ChromaDB (Staro)':<18} | {'sqlite-vec (Novo)':<18}")
    print("-" * 75)
    
    if chroma_init_ms and sqlite_init_ms:
        print(f"{'Vrijeme inicijalizacije (veze)':<35} | {chroma_init_ms:<15.2f} ms | {sqlite_init_ms:<15.2f} ms")
    if avg_chroma_query and avg_sqlite_query:
        print(f"{'Prosječno vrijeme pretrage (k=5)':<35} | {avg_chroma_query:<15.2f} ms | {avg_sqlite_query:<15.2f} ms")
        speedup = avg_chroma_query / avg_sqlite_query
        print("-" * 75)
        print(f"🚀 sqlite-vec pretraga je {speedup:.1f}x brža od ChromaDB-a!")
    print("======================================================================")

if __name__ == "__main__":
    run_comparison()
