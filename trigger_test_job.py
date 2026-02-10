
import requests
import json
import time

def trigger_forbidden_ingest():
    url = "http://localhost:8000/jobs"
    payload = {
        "type": "ingest",
        "params": {
            "path": "docs/forbidden_code.py",
            "project": "default"
        },
        "priority": 10
    }
    print(f"🚀 Šaljem zahtjev za ingest 'forbidden_code.py' na {url}...")
    resp = requests.post(url, json=payload)
    print(f"✅ Odgovor: {resp.json()}")

if __name__ == "__main__":
    trigger_forbidden_ingest()
