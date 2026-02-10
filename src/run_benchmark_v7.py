import requests
import time
import json
import statistics
from typing import List, Dict

API_URL = "http://127.0.0.1:8000/query"
GOLDEN_SET_PATH = "benchmarks/golden_set.json"

def run_benchmark():
    print("🚀 Pokrećem Kronos Benchmark (v7.0)...")
    
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    total_latency = 0
    passed = 0
    
    for case in cases:
        query = case['query']
        expected = case['expected_substrings']
        max_lat = case.get('max_latency_ms', 2000)
        
        print(f"\n❔ Query: '{query}'")
        
        start = time.time()
        try:
            resp = requests.post(API_URL, json={"text": query, "mode": "auto"}, timeout=10)
            lat = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                print(f"❌ Server Error: {resp.status_code}")
                results.append({"query": query, "status": "FAIL", "latency": lat})
                continue
                
            data = resp.json()
            context: str = data.get("context", "")
            tokens_used = data.get("stats", {}).get("used_tokens", 0)
            
            # Check Recall (Simple substring match)
            found = [s for s in expected if s.lower() in context.lower()]
            success = len(found) > 0 # At least one match
            
            status = "PASS" if success else "FAIL"
            if success: passed += 1
            
            emoji = "✅" if success else "❌"
            latency_emoji = "🐢" if lat > max_lat else "⚡"
            
            print(f"{emoji} Status: {status} | {latency_emoji} Latency: {lat:.0f}ms | 🧠 Tokens: {tokens_used}")
            if not success:
                print(f"   Missing: {expected}")
                # print(f"   Got: {context[:200]}...")
            
            results.append({
                "query": query,
                "status": status,
                "latency": lat,
                "tokens": tokens_used
            })
            total_latency += lat
            
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            
    # Summary
    print("\n" + "="*40)
    print(f"📊 BENCHMARK SUMMARY")
    print("="*40)
    print(f"Total Cases: {len(cases)}")
    print(f"Passed:      {passed} ({passed/len(cases)*100:.0f}%)")
    avg_lat = total_latency / len(cases) if cases else 0
    print(f"Avg Latency: {avg_lat:.0f}ms")
    
    tokens = [r['tokens'] for r in results if 'tokens' in r]
    avg_tok = statistics.mean(tokens) if tokens else 0
    print(f"Avg Tokens:  {avg_tok:.0f}")

if __name__ == "__main__":
    run_benchmark()
