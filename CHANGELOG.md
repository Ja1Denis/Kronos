# Changelog

All notable changes to the **Kronos** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.7.3] - 2026-06-07
### Added
- **Asynchronous Ingestion**: Heavy operations like `kronos_ingest` are now processed in the background, returning a `job_id` immediately to prevent client timeouts.
- **Query Streaming**: Real-time search phase updates and incremental chunk/entity streaming in `kronos_query` via SSE.
- **MCP Server Card**: Standardized server metadata at `kronos://meta/card` (using `mcp-server-card.json`).

### Fixed
- **Windows UTF-8 Stability**: Forced UTF-8 stdio encoding for the MCP server on Windows to resolve emoji encoding crashes.

## [v0.7.2] - 2026-06-07
### Added
- **Self-RAG Loop**: Evaluates context sufficiency using an LLM evaluator; automatically runs a secondary re-query if context is deemed insufficient.
- **Self-RAG MCP Support**: Added `self_rag` parameters to `kronos_query` and `kronos_search`.

### Fixed
- **SQLite Schema Migration**: Resolved Windows migration issue when adding graph edge/node columns with non-constant defaults.

## [v0.7.1] - 2026-06-06
### Fixed
- **Windows DB Lock**: Explicitly release the Rust engine SQLite connection reference on close to prevent DB lock issues on Windows.

## [v0.7.0] - 2026-06-06
### Added
- **Temporal Knowledge Graph**: Tracks time-domain validity (`valid_from` and `valid_to`) of nodes and edges.
- **Soft-Delete Ingestion**: Instead of hard-deleting elements, obsolete code elements are now marked as inactive.
- **Active Edge Filtering**: Automated Python/Rust BFS and query filtering to query only active relationships (`valid_to IS NULL`).

## [v0.6.1] - 2026-02-17
### Added
- **Disk-Based Knowledge Graph**: SQLite-powered graph storage for low-RAM usage and cross-project knowledge transfer.
- **Improved README**: Complete overhaul and translation to English, featuring real-world Case Studies.
- **MIT License**: Official licensing with author credit to Denis Sakač.
- **CONTRIBUTING.md**: Guidelines for community contributions.

### Fixed
- **Database Locking**: Resolved multi-agent concurrency issues on Windows using WAL mode.
- **CLI Stability**: Improved output rendering for Windows terminals.

---

## [v0.6.0] - 2026-02-16
### Added
- **Knowledge Graph (Phase 14)**: Initial implementation of the `DiskKnowledgeGraph` module.
- **Pattern Matching**: Ability to recognize architectural patterns across different projects.

---

## [v0.5.1] - 2026-02-14
### Added
- **Multi-Agent SSE Support**: Server-client architecture via SSE transport and MCP Bridge.
- **Job Reliability**: Enhanced background worker thread for massive ingestion.

### Changed
- **Database Optimization**: Enabled WAL mode by default for concurrent access.

---

## [v0.5.0] - 2026-02-13
### Added
- **Shadow Accounting**: Built-in tracking of token savings and ROI in every response.
- **SavingsLedger**: Persistent storage for financial efficiency metrics.
- **Dynamic Pricing**: Support for different LLM pricing models.

---

## [v0.4.0] - 2026-02-12
### Added
- **The Pointer Revolution**: Implementation of lightweight references instead of full text blocks.
- **Context Budgeter**: Dynamic token management (Light/Auto/Extra modes).
- **Gemini 2.0 Flash Integration**: Full production API support.

---

## [v0.3.0] - 2026-02-11
### Added
- **Rust Fast-Path**: L0/L1 literal match search implemented in Rust for < 1ms latency.
- **Hybrid Search Stage 1**: Keywords filtering before semantic search.

---

## [v0.2.0] - 2026-02-10
### Added
- **Asynchronous Architecture**: `JobManager` and background workers for non-blocking ingestion.
- **MCP Server**: Initial implementation of the Model Context Protocol.
- **Proactive Analyst**: Detection of contradictions and project inconsistencies.

---

## [v0.1.0] - 2026-02-08
### Added
- **Initial Release**: Basic RAG functionality with ChromaDB and SQLite.
- **Event Sourcing**: Core data integrity through `archive.jsonl`.
