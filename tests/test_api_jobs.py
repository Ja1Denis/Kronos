import unittest
from fastapi.testclient import TestClient
from src.server import app
import os
import shutil

class TestJobApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Ensure clean state if possible, though server uses real DB path potentially
        # For separate testing, we might want to mock DB path, but for integration fine.

    def test_jobs_endpoints(self):
        # 1. Submit Job
        payload = {"type": "test_job", "params": {"foo": "bar"}, "priority": 8}
        response = self.client.post("/jobs", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        job_id = data["id"]
        
        # 2. Get Job
        response = self.client.get(f"/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], job_id)
        self.assertEqual(data["params"]["foo"], "bar")
        self.assertEqual(data["priority"], 8)
        
        # 3. Cancel Job
        response = self.client.delete(f"/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")
        
        # Verify cancelled
        response = self.client.get(f"/jobs/{job_id}")
        data = response.json()
        self.assertEqual(data["status"], "cancelled")

    def test_job_not_found(self):
        response = self.client.get("/jobs/non_existent_id")
        self.assertEqual(response.status_code, 404)

