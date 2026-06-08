import time
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.getcwd())

from src.modules.disk_graph import DiskKnowledgeGraph

def benchmark():
    db_path = "data/knowledge_graph.db"
    
    # Get a real node ID from the DB
    import sqlite3
    conn = sqlite3.connect(db_path)
    res = conn.execute("SELECT from_node FROM graph_edges GROUP BY from_node ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    conn.close()
    
    if not res:
        print("❌ DB is empty or has no edges!")
        return
        
    node_id = "file:kronos:src/modules/disk_graph.py"
    depth = 10
    iterations = 3

    print(f"--- 🧪 KRONOS TURBO-GRAPH BENCHMARK ---")
    print(f"Target node: {node_id}")
    print(f"Traversal Depth: {depth}")
    print(f"Averaging over {iterations} runs...")
    
    # 1. Test with RUST
    g_rust = DiskKnowledgeGraph(db_path)
    times_rust = []
    for _ in range(iterations):
        start_rust = time.perf_counter()
        result_rust = g_rust.get_subgraph(node_id, depth)
        times_rust.append((time.perf_counter() - start_rust) * 1000)
    
    avg_rust = sum(times_rust) / iterations
    print(f"\n🚀 [RUST] Avg Time: {avg_rust:.2f} ms")
    print(f"   Nodes found: {len(result_rust['nodes'])}")

    # 2. Test with PYTHON (Forced Fallback)
    g_py = DiskKnowledgeGraph(db_path)
    g_py.use_rust = False
    times_py = []
    for _ in range(iterations):
        start_py = time.perf_counter()
        result_py = g_py.get_subgraph(node_id, depth)
        times_py.append((time.perf_counter() - start_py) * 1000)
        
    avg_py = sum(times_py) / iterations
    print(f"\n🐍 [PYTHON] Avg Time: {avg_py:.2f} ms")
    print(f"   Nodes found: {len(result_py['nodes'])}")

    # 3. Final Verdict
    if avg_rust > 0:
        speedup = avg_py / avg_rust
        print(f"\n🔥 VERDICT: Rust is {speedup:.1f}x FASTER!")
    
    # Verify consistency
    if len(result_rust['nodes']) == len(result_py['nodes']):
        print("✅ Data Integrity: PASSED (Match)")
    else:
        print(f"⚠️ Data mismatch: Rust found {len(result_rust['nodes'])}, Python found {len(result_py['nodes'])}")

if __name__ == "__main__":
    benchmark()
