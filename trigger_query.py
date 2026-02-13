import requests
import sys

try:
    print("Sending request to http://localhost:8000/query ...")
    r = requests.post('http://localhost:8000/query', json={'text': 'Daj mi detalje o T034.'}, timeout=15)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:200]}...")
except Exception as e:
    print(f"ERROR: {e}")
