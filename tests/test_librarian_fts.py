import pytest
import sys
import os

# Dodajemo src u path kako bi mogli uvoziti module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.modules.librarian import Librarian

def test_fts_sanitization():
    """Test da specijalni znakovi ne uzrokuju syntax error"""
    lib = Librarian()
    
    # Test problematičnih tokena koristeći _escape_fts_token (jer je to stvarna metoda u Librarianu)
    assert lib._escape_fts_token("sys.path.append()") == '"sys.path.append()"'
    assert lib._escape_fts_token("try:") == '"try:"'
    assert lib._escape_fts_token("r = requests") == 'r = requests'
    assert lib._escape_fts_token("-") == ""
    assert lib._escape_fts_token("") == ""

def test_fts_query_logic():
    """Test da generirani query logike radi (AND/OR)"""
    lib = Librarian()
    
    # Napomena: search_fts zapravo izvršava query na DB-u. 
    # Ovdje testiramo da bar ne crasha pri pozivu sa čudnim znakovima.
    try:
        results = lib.search_fts("sys.path.append() try:", limit=1)
        # Očekujemo listu (može biti prazna ako nema podataka, ali ne smije crashati)
        assert isinstance(results, list)
    except Exception as e:
        pytest.fail(f"search_fts crashed with exception: {e}")
