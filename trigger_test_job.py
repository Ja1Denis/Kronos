import httpx
import time

def trigger_test():
    url = "http://localhost:8000/jobs"
    print(f"🚀 Šaljem testni posao na {url}...")
    
    with httpx.Client() as client:
        resp = client.post(url, json={
            "type": "test_job",
            "params": {"duration": 5},
            "priority": 10
        })
        print(f"✅ Odgovor: {resp.json()}")

if __name__ == "__main__":
    trigger_test()
