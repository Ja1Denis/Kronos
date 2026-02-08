import pytest
import os
import shutil
import sqlite3
from src.modules.librarian import Librarian
from src.modules.extractor import Extractor

@pytest.fixture
def temp_data_dir(tmp_path):
    """Fixture koji kreira privremeni direktorij za testne podatke."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)

def test_librarian_init(temp_data_dir):
    lib = Librarian(temp_data_dir)
    assert os.path.exists(os.path.join(temp_data_dir, "metadata.db"))

def test_extractor_problems_solutions():
    extractor = Extractor()
    text = """
Problem: Sustav se sporo pokreće.
Rješenje: Dodati indeksiranje u pozadini.
Odluka: Koristit ćemo FastAPI.
    """
    data = extractor.extract(text)
    assert "Sustav se sporo pokreće." in data["problems"]
    assert "Dodati indeksiranje u pozadini." in data["solutions"]
    assert "Koristit ćemo FastAPI." in data["decisions"]

def test_extractor_tasks():
    extractor = Extractor()
    text = """
- [ ] Napraviti testove
- [x] Implementirati API
    """
    data = extractor.extract(text)
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["status"] == "todo"
    assert data["tasks"][1]["status"] == "done"

def test_librarian_entities_storage(temp_data_dir):
    lib = Librarian(temp_data_dir)
    test_data = {
        "problems": ["Test problem"],
        "solutions": ["Test solution"],
        "tasks": [{"status": "todo", "content": "Test task"}]
    }
    lib.store_extracted_data("test_path.md", test_data)
    
    conn = sqlite3.connect(lib.meta_path)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM entities")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count == 3
