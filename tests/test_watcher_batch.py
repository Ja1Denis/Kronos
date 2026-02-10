import os
import time
import shutil
import unittest
from src.modules.job_manager import JobManager
from src.modules.watcher import Watcher

class TestWatcherBatch(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/test_watcher_batch"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Očisti jobs.db za test (ako postoji)
        self.db_path = "data/jobs.db"
        self.manager = JobManager(db_path=self.db_path)
        
        # Pokreni Watcher s kratkim debounce-om
        self.watcher = Watcher(path=self.test_dir, debounce=1.0)
        self.watcher.start()

    def tearDown(self):
        self.watcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_batch_submission(self):
        # 1. Kreiraj/Promijeni više datoteka brzo
        for i in range(5):
            file_path = os.path.join(self.test_dir, f"file_{i}.md")
            with open(file_path, "w") as f:
                f.write(f"Sadržaj datoteke {i}")
            time.sleep(0.1)
            
        # 2. Čekaj da debounce timer odradi svoje
        print("Waiting for batch timer...")
        time.sleep(2.0)
        
        # 3. Provjeri bazu (tražimo 'ingest_batch' job)
        next_job = self.manager.get_next_job()
        self.assertIsNotNone(next_job, "Job nije kreiran")
        self.assertEqual(next_job["type"], "ingest_batch")
        
        files = next_job["params"].get("files", [])
        print(f"Pronađeno datoteka u batchu: {len(files)}")
        self.assertGreaterEqual(len(files), 1)
        
if __name__ == '__main__':
    unittest.main()
