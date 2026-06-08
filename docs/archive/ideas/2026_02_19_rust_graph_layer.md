# Idea: Kronos Graph Layer Optimization (Rust Hybrid)

## Overview
Currently, the Kronos Knowledge Graph traversal (BFS/DFS) is implemented in Python, leading to N-query performance issues (200-500ms latency). This optimization project aims to move the graph traversal logic to a high-performance Rust extension using PyO3 and Recursive CTEs.

## Brainstorming & Architecture
- **Language**: Rust 1.84+ with PyO3 for Python bindings.
- **Database Access**: `rusqlite` for direct, low-overhead access to `knowledge_graph.db`.
- **Schema Alignment**:
    - Tables: `graph_nodes`, `graph_edges` (different from initial prompt).
    - Columns: `from_node`, `to_node`, `relationship_type` (mapped to `source`, `target`, `type`).
- **Primary Optimization**: Replace multiple Python-driven SQLite calls with a single Recursive Common Table Expression (CTE) in Rust.
- **Hybrid Model**: 
    - Rust handles specialized, heavy-lifting graph queries.
    - Python remains the orchestrator for high-level logic (Oracle, RAG).

## Performance Goals
- **Current Latency**: 200-800ms per deep traversal.
- **Target Latency**: <50ms (10-20x speedup).
- **Complexity**: O(N) queries in Python -> O(1) query in Rust engine.

## Implementation Phases
### Phase 1: Setup & Hello World
- Cargo environment initialization.
- PyO3 scaffolding.
- Basic IPC/Call verification.

### Phase 2: Core Rust Engine
- SQLite connection management (`rusqlite`).
- **Recursive CTE for BFS** (`get_related` equivalent).
- **Subgraph Extraction** (`get_subgraph` equivalent - critical for RAG context).
- Shortest path finding (`find_path` BFS/Dijkstra).

### Phase 3: Python Wrapper & Fallback
- Integration into `DiskKnowledgeGraph` class.
- Automated fallback logic if Rust binary is missing.

### Phase 4: Benchmarking & Validation
- Latency comparison reports.
- Memory usage tracking.

## Visual Architecture

```text
      TRENUTNO (Sporo)                        PLANIRANO (Brzo)
    +-----------------------+              +-----------------------+
    |    Python Oracle      |              |    Python Oracle      |
    +----------+------------+              +----------+------------+
               |                                      |
               v                                      v
    +----------+------------+              +----------+------------+
    |  DiskKnowledgeGraph   |              |  DiskKnowledgeGraph   |
    |       (Python)        |              |    (Hybrid Wrapper)   |
    +----------+------------+              +----------+------------+
               |                               |            |
      [Petlja / Loop]                          |      (Fallback)
     for i in depth:                           |            |
        SQL Query <----------+                 |            v
               |             |          (Brzi Put)   +-------------+
               | (N puta!)   |                 |     |  Legacy Py  |
               v             |                 v     |     BFS     |
    +----------+------------+ |         +-------------+-------------+
    |  SQLite Database      | |         |   RUST GRAPH ENGINE (🦀)  |
    |  (knowledge_graph.db) | |         |  - Compiled PyO3 Module   |
    +-----------------------+ |         |  - Recursive CTE Query    |
               |              |         +-------------+-------------+
               +--------------+                       |
                                             (Samo 1 SQL Query!)
                                                      v
                                            +-----------------------+
                                            |  SQLite Database      |
                                            |  (knowledge_graph.db) |
                                            +-----------------------+
```

## Questions to Resolve
...

**Status**: Brainstorming / Planning
**Date**: 2026-02-19
