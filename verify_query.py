import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from modules.oracle import Oracle

def main():
    print("Inicijalizacija Oracle-a...")
    try:
        oracle = Oracle(os.path.join(os.path.dirname(__file__), 'data', 'store'))
        print("Oracle spreman!")
        
        query = "Što bi Denis dodao u kurikulum za 2. razred prema datoteci opisZadataka.md?"
        print(f"Upit: {query}")
        
        results = oracle.ask(query, limit=5)
        
        if not results:
            print("Nema rezultata.")
            return

        print("\n--- Rezultati ---")
        # Handle entities
        for ent in results.get('entities', []):
            print(f"[ENTITY] {ent.get('content')[:100]}...")
            
        # Handle chunks
        for chunk in results.get('chunks', []):
            print(f"[CHUNK] {chunk.get('content')[:200]}...")
            print(f"Source: {chunk.get('metadata', {}).get('source')}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Greška: {e}")

if __name__ == "__main__":
    main()
