import os
import time
import pytest
import shutil
from src.modules.watcher import Watcher
from src.modules.ingestor import Ingestor
from src.modules.librarian import Librarian
import sqlite3

@pytest.fixture
def test_env(tmp_path):
    # Setup test directory
    watch_dir = tmp_path / "watch"
    watch_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Mock ingestor with custom data path
    class TestIngestor(Ingestor):
        def __init__(self, db_path):
            from src.modules.librarian import Librarian
            from src.modules.oracle import Oracle
            from src.modules.extractor import Extractor
            self.chunk_size = 1000
            self.librarian = Librarian(db_path)
            self.oracle = Oracle(os.path.join(db_path, "store"))
            self.extractor = Extractor()

    ingestor = TestIngestor(str(data_dir))
    return str(watch_dir), str(data_dir), ingestor

def test_watcher_detect_file(test_env):
    watch_dir, data_dir, ingestor = test_env
    
    from src.modules.watcher import KronosHandler
    from watchdog.observers import Observer
    
    handler = KronosHandler(ingestor)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()
    
    try:
        # Create a new file
        test_file = os.path.join(watch_dir, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Test Title\nThis is a test content.")
            
        # Give some time for watcher and processing
        time.sleep(2)
        
        # Check if indexed in SQLite FTS
        db_path = os.path.join(data_dir, "metadata.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM knowledge_fts WHERE content LIKE '%Test Title%'")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count > 0
        
    finally:
        observer.stop()
        observer.join()
