# Kronos Core Optimization - Performance & Savings

## Vision
Making the "scalpel" sharper. Maximizing precision and minimizing token waste at the source.

## Priority 1: Semantic & Structural Chunking
- **Function-Aware Splitter:** Instead of splitting by lines, split by function and class boundaries.
- **Contextual Anchors:** Attach parent class names or function signatures to every child chunk for better retrieval.

## Priority 2: Incremental Indexing
- **Diff-Aware Updates:** When a file is modified, identify the exact chunk that changed and only update those embeddings.
- **Hash Checks:** Prevent redundant LLM calls for unchanged files.

## Priority 3: Entity Extraction Refinement
- **Zero-Shot Decision Mining:** Improve the "Decision" and "Problem" extraction prompts.
- **Temporal Linking:** Better automated history tracking for how decisions evolve over time.

## Priority 4: Search Latency
- **Lightweight Vector Engine:** Investigation into FAISS or HNSW alternatives for faster local-first search.
- **Keyword Boosting:** Fine-tuning the 0.3-0.5 FTS boost factor based on project type.

## Status: TOP PRIORITY (Next Phase)
These improvements provide the highest ROI for daily usage.
