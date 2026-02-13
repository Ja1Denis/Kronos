import pytest
import requests
import time
import subprocess
import os
import sys

# Dodajemo src u path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="module")
def server_url():
    """Vraća URL servera. Ako server nije pokrenut, pokreće ga."""
    url = "http://127.0.0.1:8000"
    try:
        requests.get(f"{url}/health", timeout=1)
        print("✅ Using already running server on 8000")
        return url
    except requests.exceptions.ConnectionError:
        print("🚀 Starting new server for integration tests...")
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        
        proc = subprocess.Popen(
            ["python", "src/server.py"],
            env=env,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        )
        
        # Čekaj da se server podigne
        for _ in range(15):
            try:
                requests.get(f"{url}/health", timeout=1)
                break
            except:
                time.sleep(1)
        else:
            proc.terminate()
            pytest.fail("Server failed to start")
            
        return url

def test_query_api(server_url):
    """Test /query endpointa"""
    payload = {
        "text": "Što je cilj projekta Kronos?",
        "mode": "light"
    }
    response = requests.post(f"{server_url}/query", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "context" in data
    print(f"✅ API Response tokens: {data['stats']['used_tokens']}")

def test_health_metrics(server_url):
    """Test da /health vraća nove metriku"""
    response = requests.get(f"{server_url}/health")
    assert response.status_code == 200
    data = response.json()
    assert "health_score" in data
    assert "fts_failure_rate" in data
    assert "vector_failure_rate" in data
    print(f"✅ Health Score: {data['health_score']}%")

def test_fts_safety_crash_test(server_url):
    """Test da upit sa specijalnim znakovima ne ruši server"""
    malicious_query = "sys.path.append('..'); # OR 1=1 -- '\""
    payload = {"text": malicious_query, "mode": "light"}
    
    response = requests.post(f"{server_url}/query", json=payload, timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success" # Treba vratiti success (prazan ili pun), ali ne 500
    print("✅ Malicious FTS query handled safely")
