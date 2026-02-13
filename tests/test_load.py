import pytest
import requests
import concurrent.futures
import time

def send_query(url):
    """Helper za slanje jednog requesta"""
    payload = {"text": "Daj mi detalje o T034", "mode": "light"}
    try:
        response = requests.post(f"{url}/query", json=payload, timeout=20)
        return response.status_code == 200
    except Exception as e:
        print(f"Request failed: {e}")
        return False

def test_concurrent_load():
    """Testira performanse pod opterećenjem"""
    url = "http://127.0.0.1:8000"
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
