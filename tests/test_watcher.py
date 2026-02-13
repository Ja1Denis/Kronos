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
    
    from src.modules.watcher import BatchJobEventHandler
    from src.modules.job_manager import JobManager
    from watchdog.observers import Observer
    import uuid
    
    # Koristimo kraći debounce interval za testove i testnu bazu za jobove
    test_jobs_db = os.path.join(data_dir, "test_jobs.db")
    job_manager = JobManager(db_path=test_jobs_db)
    
    handler = BatchJobEventHandler(debounce_interval=0.5)
    # Monkey-patch job manager za test
    handler.job_manager = job_manager
    
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()
    
    try:
        # Create a new file
        test_file = os.path.join(watch_dir, "test.md")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# Test Title\nThis is a test content.")
            
        # Give some time for watcher and processing (debounce + processing)
        time.sleep(2)
        
        # Provjeri je li kreiran job u testnoj bazi
        jobs = job_manager.list_jobs()
        assert len(jobs) > 0
        assert jobs[0]['type'] == 'ingest_batch'
        
    finally:
        observer.stop()
        observer.join()
