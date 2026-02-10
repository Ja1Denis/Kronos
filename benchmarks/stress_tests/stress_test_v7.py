import requests
import threading
import time
import random
import json

API_URL = "http://127.0.0.1:8000/query"
CONCURRENT_REQUESTS = 10  # Broj istovremenih threadova
TOTAL_REQUESTS = 30       # Ukupan broj upita

queries = [
    "Što je Kronos?",
    "Kako radi Context Budgeter?",
    "Daj mi detalje o T034 zadatku.",
    "Opiši arhitekturu sustava.",
    "Tko je autor projekta?"
]

trace_sample = """Traceback (most recent call last):
  File 'src/server.py', line 125, in query_memory
    result = oracle.ask(text)
ERROR: Database is locked"""

stats = {
    "success": 0,
    "error": 0,
    "latencies": []
}
stats_lock = threading.Lock()

def send_request(id):
    query = random.choice(queries)
    is_debug = random.random() > 0.5
    
    payload = {
        "text": query,
        "mode": "auto"
    }
    if is_debug:
        payload["stack_trace"] = trace_sample
        payload["mode"] = "debug"

    start = time.time()
    try:
        resp = requests.post(API_URL, json=payload, timeout=15)
        latency = (time.time() - start) * 1000
        
        with stats_lock:
            if resp.status_code == 200:
                stats["success"] += 1
                stats["latencies"].append(latency)
                print(f"[{id}] ✅ SUCCESS ({latency:.0f}ms)")
            else:
                stats["error"] += 1
                print(f"[{id}] ❌ ERROR {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        with stats_lock:
            stats["error"] += 1
        print(f"[{id}] 💀 FAILED: {e}")

def run_stress_test():
    print(f"🔥 Započinjem stres test: {TOTAL_REQUESTS} upita, {CONCURRENT_REQUESTS} paralelno...")
    threads = []
    
    start_time = time.time()
    
    for i in range(TOTAL_REQUESTS):
        t = threading.Thread(target=send_request, args=(i,))
        threads.append(t)
        t.start()
        
        # Održavaj limit konkurentnih threadova
        if len(threads) >= CONCURRENT_REQUESTS:
            for thread in threads:
                thread.join()
            threads = []

    for t in threads:
        thread.join()
        
    total_time = time.time() - start_time
    
    print("\n" + "="*40)
    print("📊 REZULTATI STRES TESTA")
    print("="*40)
    print(f"Ukupno upita:   {TOTAL_REQUESTS}")
    print(f"Uspješno:       {stats['success']}")
    print(f"Greške:          {stats['error']}")
    if stats["latencies"]:
        avg_lat = sum(stats["latencies"]) / len(stats["latencies"])
        print(f"Prosječna latencija: {avg_lat:.0f}ms")
        print(f"Najbrži upit:    {min(stats['latencies']):.0f}ms")
        print(f"Najsporiji upit: {max(stats['latencies']):.0f}ms")
    print(f"Ukupno vrijeme: {total_time:.1f}s")
    print("="*40)

if __name__ == "__main__":
    run_stress_test()
