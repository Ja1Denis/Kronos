import requests
import threading
import time
import random
import os

API_URL = "http://127.0.0.1:8000/query"
DURATION_SECONDS = 20
DUMMY_FILE = "simulated_work.md"

# Statistika
stats = {"reads": 0, "writes": 0, "errors": 0, "latencies": []}
stats_lock = threading.Lock()
stop_event = threading.Event()

def simulate_editor(id):
    """Simulira developera koji često sprema fajlove (triggera Ingestor)"""
    while not stop_event.is_set():
        try:
            timestamp = time.time()
            with open(DUMMY_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n- [Update] Developer {id} working at {timestamp}")
            
            # Nasumična pauza (tipkanje kodera)
            time.sleep(random.uniform(1.0, 3.0))
            with stats_lock:
                stats["writes"] += 1
            print(f"📝 [Editor {id}] Saved file (Triggering Ingestion)")
        except Exception as e:
            print(f"📝 [Editor {id}] Error writing: {e}")

def simulate_developer(id):
    """Simulira agenta koji postavlja pitanja"""
    questions = [
        "Kako radi Singleton Oracle?",
        "Objasni Three Corpses strategiju.",
        "Koji je limit za light profil?",
        "Tko je Denis?",
        "Analiziraj server.py"
    ]
    
    while not stop_event.is_set():
        query = random.choice(questions)
        start = time.time()
        try:
            resp = requests.post(API_URL, json={"text": query, "mode": "auto"}, timeout=10)
            lat = (time.time() - start) * 1000
            
            with stats_lock:
                if resp.status_code == 200:
                    stats["reads"] += 1
                    stats["latencies"].append(lat)
                    print(f"🧠 [Dev {id}] Answered in {lat:.0f}ms")
                else:
                    stats["errors"] += 1
                    print(f"🧠 [Dev {id}] ERROR {resp.status_code}")
        except Exception as e:
            with stats_lock:
                stats["errors"] += 1
            print(f"🧠 [Dev {id}] FAILED: {e}")
        
        time.sleep(random.uniform(0.5, 2.0))

def simulate_debugger(id):
    """Simulira situaciju s greškom (Log fetch + Stack Trace)"""
    trace = """Traceback (most recent call last):
      File 'src/server.py', line 99, in main
        raise ValueError("Simulated Crash")
    ValueError: Simulated Crash"""
    
    while not stop_event.is_set():
        try:
            start = time.time()
            payload = {
                "text": "Popravi ovaj crash", 
                "stack_trace": trace,
                "mode": "debug"
            }
            resp = requests.post(API_URL, json=payload, timeout=15)
            lat = (time.time() - start) * 1000
            
            with stats_lock:
                if resp.status_code == 200:
                    stats["reads"] += 1
                    stats["latencies"].append(lat)
                    print(f"🐞 [Debug {id}] Logs analyzed in {lat:.0f}ms")
                else:
                    stats["errors"] += 1
                    print(f"🐞 [Debug {id}] ERROR {resp.status_code}")
        except Exception as e:
            print(f"🐞 [Debug {id}] FAILED: {e}")
        
        time.sleep(random.uniform(3.0, 6.0))

def run_real_test():
    print(f"🎬 Action! Simulating busy dev environment for {DURATION_SECONDS}s...")
    
    # Clean setup
    with open(DUMMY_FILE, "w") as f:
        f.write("# Simulated Work Log\n")

    threads = []
    # 2 Editora (Writes)
    for i in range(2):
        t = threading.Thread(target=simulate_editor, args=(i,))
        threads.append(t)
        t.start()
        
    # 2 Developera (Standard Reads)
    for i in range(2):
        t = threading.Thread(target=simulate_developer, args=(i,))
        threads.append(t)
        t.start()
        
    # 1 Debugger (Heavy Reads + Log Access)
    t = threading.Thread(target=simulate_debugger, args=(0,))
    threads.append(t)
    t.start()
    
    # Run loop
    time.sleep(DURATION_SECONDS)
    stop_event.set()
    
    for t in threads:
        t.join()
        
    # Cleanup
    if os.path.exists(DUMMY_FILE):
        os.remove(DUMMY_FILE)

    print("\n" + "="*40)
    print("📊 REALISTIC SCENARIO REPORT")
    print("="*40)
    print(f"File Writes (Ingestions): {stats['writes']}")
    print(f"Assistant Queries:        {stats['reads']}")
    print(f"Failures (500/Timeout):   {stats['errors']}")
    if stats["latencies"]:
        avg = sum(stats["latencies"]) / len(stats["latencies"])
        print(f"Avg Latency:              {avg:.0f}ms")
    print("="*40)

if __name__ == "__main__":
    run_real_test()
