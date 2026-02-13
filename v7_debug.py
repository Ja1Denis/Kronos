import os
import sys
# Fix for SentenceTransformers/HuggingFace crash on Windows
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from colorama import Fore, Style

# Ensure project root is in path
sys.path.append(os.getcwd())

def test_query():
    print("Testing Oracle.ask('Što je Kronos?')...")
    from src.modules.oracle import Oracle
    oracle = Oracle()
    
    # Simulate server call
    print("Calling oracle.ask...")
    try:
        res = oracle.ask("Što je Kronos?", limit=30, silent=False)
        print(f"SUCCESS! Result type: {res.get('type')}")
        print(f"Chunks found: {len(res.get('chunks', []))}")
    except Exception as e:
        print(f"FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
    except BaseException as e:
        print(f"FAILED with critical error: {type(e)}")

if __name__ == "__main__":
    test_query()
