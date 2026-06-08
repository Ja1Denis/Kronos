import pytest
import sqlite3
import sqlite_vec
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle

@pytest.fixture(scope="function")
def librarian():
    """Dohvaća Librarian instancu"""
    return Librarian()

@pytest.fixture(scope="function")
def oracle():
    """Dohvaća Oracle instancu"""
    return Oracle()

def test_sqlite_vec_extension_loaded(librarian):
    """Test da se sqlite-vec ekstenzija ispravno učitava na SQLite konekciju"""
    conn = librarian._get_sqlite_conn()
    try:
        res = conn.execute("select vec_version()").fetchone()
        assert res is not None
        assert res[0].startswith("v0")
        print(f"✅ sqlite-vec verzija: {res[0]}")
    except Exception as e:
        pytest.fail(f"Failed to load sqlite-vec: {e}")
    finally:
        conn.close()

def test_vector_table_creation(librarian):
    """Test da su virtualne tablice za vektore ispravno kreirane"""
    conn = librarian._get_sqlite_conn()
    try:
        # Provjera vec_items
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vec_metadata'")
        assert cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vec_items'")
        assert cursor.fetchone() is not None
        print("✅ Vektorske tablice (vec_metadata i vec_items) postoje.")
    finally:
        conn.close()

def test_basic_semantic_search(oracle):
    """Test osnovnog unosa i pretrage preko Oracle klase"""
    # Za ovaj test koristimo mock ili stvarni upsert ovisno o API ključu
    if not oracle.embedding_function:
        pytest.skip("Gemini API key is not configured, skipping semantic search test.")
        
    try:
        # Pripremi podatke
        doc_id = "test_doc_999"
        doc_content = "Kronos is a hybrid search system combining sqlite-vec and FTS5."
        doc_meta = {"source": "test", "project": "test_proj"}
        
        # Upsert
        oracle.safe_upsert([doc_content], [doc_meta], [doc_id])
        
        # Query
        res = oracle.ask("What is Kronos?", project="test_proj", limit=1)
        
        assert res is not None
        # Može biti mixed_response ili chunk_response
        assert res.get("status") == "success"
        print(f"✅ Vektorska pretraga uspješna: {res}")
    except Exception as e:
        pytest.fail(f"Basic semantic search test failed: {e}")
