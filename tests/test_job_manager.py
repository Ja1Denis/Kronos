import unittest
import os
import sqlite3
import shutil
import time
from src.modules.job_manager import JobManager

class TestJobManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_data"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        self.db_path = os.path.join(self.test_dir, "jobs.db")
        self.manager = JobManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_submit_and_get_job(self):
        params = {"file": "test.txt"}
        job_id = self.manager.submit_job("ingest", params, priority=10)
        
        job = self.manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["type"], "ingest")
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["priority"], 10)
        self.assertEqual(job["params"], params)

    def test_job_lifecycle(self):
        # 1. Submit
        job_id = self.manager.submit_job("test", {})
        
        # 2. Get Next
        next_job = self.manager.get_next_job()
        self.assertIsNotNone(next_job)
        self.assertEqual(next_job["id"], job_id)
        
        # 3. Start
        started = self.manager.start_job(job_id)
        self.assertTrue(started)
        
        job = self.manager.get_job(job_id)
        self.assertEqual(job["status"], "running")
        self.assertIsNotNone(job["started_at"])
        
        # 4. Update Progress
        self.manager.update_progress(job_id, 50)
        job = self.manager.get_job(job_id)
        self.assertEqual(job["progress"], 50)
        
        # 5. Complete
        result = {"success": True}
        self.manager.complete_job(job_id, result)
        
        job = self.manager.get_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["progress"], 100)
        self.assertEqual(job["result"], result)
        self.assertIsNotNone(job["finished_at"])

    def test_priority_ordering(self):
        id1 = self.manager.submit_job("low", {}, priority=1)
        id2 = self.manager.submit_job("high", {}, priority=10)
        id3 = self.manager.submit_job("mid", {}, priority=5)
        
        # Expect High -> Mid -> Low
        job1 = self.manager.get_next_job()
        self.manager.start_job(job1["id"])
        
        job2 = self.manager.get_next_job()
        self.manager.start_job(job2["id"])
        
        job3 = self.manager.get_next_job()
        self.manager.start_job(job3["id"])
        
        self.assertEqual(job1["id"], id2)
        self.assertEqual(job2["id"], id3)
        self.assertEqual(job3["id"], id1)

    def test_cleanup(self):
        # Create a job that finished 8 days ago
        job_id = self.manager.submit_job("old", {})
        self.manager.start_job(job_id)
        self.manager.complete_job(job_id)
        
        # Manually backdate the finished_at
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        old_date = "2020-01-01T00:00:00"
        cursor.execute("UPDATE jobs SET finished_at = ? WHERE id = ?", (old_date, job_id))
        conn.commit()
        conn.close()
        
        # Run cleanup
        self.manager.cleanup_old_jobs(days=7)
        
        job = self.manager.get_job(job_id)
        self.assertIsNone(job)

if __name__ == '__main__':
    unittest.main()
