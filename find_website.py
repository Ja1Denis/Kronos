import os
import sys
from src.modules.oracle import Oracle

def main():
    print("=== SEARCHING KRONOS FOR WEBSITE THEME / PROJECT ===")
    
    oracle = Oracle()
    
    # Query for denissakac.com theme
    query = "denissakac.com theme"
    print(f"Querying for: '{query}'")
    resp = oracle.ask(query, project=None)
    
    print("\n--- RESULTS ---")
    print(f"Status: {resp.get('status')}")
    print(f"Method: {resp.get('method')}")
    print(f"Pointers found: {len(resp.get('pointers', []))}")
    
    for i, p in enumerate(resp.get('pointers', [])):
        print(f"\n[{i+1}] Source: {p.get('source')} | Project: {p.get('project')}")
        print(f"Snippet: {p.get('snippet')[:300]}...")
        
    print("\n--- VECTOR CHUNKS ---")
    print(f"Chunks found: {len(resp.get('chunks', []))}")
    for i, c in enumerate(resp.get('chunks', [])):
        print(f"\n[{i+1}] Score: {1.0 - c.get('distance', 1.0):.4f}")
        print(f"Content: {c.get('content')[:300]}...")

if __name__ == "__main__":
    # Ensure src package is visible
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    main()
