import pytest
import requests
import concurrent.futures
import time
import subprocess
import os
import sys

@pytest.fixture(scope="module")
def server_url():
    """Vraća URL servera. Ako server nije pokrenut, pokreće ga."""
    url = "http://127.0.0.1:8000"
    proc = None
    try:
        resp = requests.get(f"{url}/health", timeout=1)
        if resp.status_code == 200 and "health_score" in resp.json():
            print("✅ Using already running server on 8000")
            yield url
            return
    except Exception:
        pass
        
    print("🚀 Starting new server for load tests...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "src/server.py"],
        env=env,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    )
    
    # Čekaj da se server podigne
    for _ in range(15):
        try:
            resp = requests.get(f"{url}/health", timeout=1)
            if resp.status_code == 200:
                break
        except:
            time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("Server failed to start")
        
    yield url
    
    if proc:
        print("🛑 Terminating test server...")
        proc.terminate()
        proc.wait()

def send_query(url):
    """Helper za slanje jednog requesta"""
    payload = {"text": "Daj mi detalje o T034", "mode": "light"}
    try:
        response = requests.post(f"{url}/query", json=payload, timeout=20)
        return response.status_code == 200
    except Exception as e:
        print(f"Request failed: {e}")
        return False

def test_concurrent_load(server_url):
    """Testira performanse pod opterećenjem"""
    url = server_url
    num_requests = 10
    max_workers = 4
    
    print(f"🚀 Starting load test: {num_requests} requests with {max_workers} workers")
    
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda _: send_query(url), range(num_requests)))
    
    duration = time.time() - start_time
    success_count = sum(results)
    
    print(f"✅ Load Test Finished in {duration:.2f}s")
    print(f"📊 Success: {success_count}/{num_requests} ({(success_count/num_requests)*100:.1f}%)")
    print(f"⚡ Average speed: {duration/num_requests:.2f}s per request")
    
    assert success_count == num_requests
