# Changelog

All notable changes to the **Kronos** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.9.8-alpha] - 2026-09-29
### Added
- **`kronos_jev_decide` — `score` tip pitanja**: ocjena na skali 2-10 razina (`score_levels` parametar). Score je vjerojatnosno težište i može pasti između razina; u odgovoru dolaze `legend` i `probabilities`. Primjena: LeadGen lead ranking, ocjena kvalitete pitcha.
- **`kronos_jev_decide` — fan-out mod**: `questions` parametar prima dict više pitanja različitih tipova (choice/noul/score) u JEDNOM pozivu — npr. pitch QA gate (cijena, završna rečenica, URL, ton, kvaliteta) u jednom Jev pozivu umjesto pet. Uključena validacija tipova prije slanja.
- Inspirirano disler/ten-levels-of-jev (wire contract za score: weighted position + legend + probabilities).
- Testovi: 9 (mock) + live smoke test na OpenRouter decisions endpointu (score 0,92s; fan-out 4 pitanja 0,75s).
### Backward compatibility
- Stari pozivi (choice/noul s postojećim parametrima) rade neizmijenjeno; svi novi parametri su optional.

---

## [v0.9.7-alpha] - 2026-09-18
### Added
- **Inkrementalna Ingestacija (SHA-256)**: Tablica `file_hashes` prati otiske datoteka. Nepromijenjene datoteke se preskaču u milisekundi ($0.00 troška, 0 API tokena).
- **Zastavica `--force` / `-f`**: Omogućuje forsirani re-ingest svih datoteka po želji.
- **OpenRouter LLMClient**: Potpuna zamjena Geminija s modelom `openai/gpt-4o-mini` za Self-RAG re-query petlju.
- **Optimizacija Baze (`kronos optimize`)**: CLI naredba za izvršavanje `PRAGMA wal_checkpoint(TRUNCATE)`, `PRAGMA optimize` i `VACUUM`.
- **Dynamic MCP Server Card**: `kronos://meta/card` resurs dinamički reflektira `src.config.__version__`.

### Fixed
- **SQLite Concurrency Deadlock**: `store_extracted_data` zatvara SQLite transakciju prije indeksiranja entiteta, rješavajući `database is locked` greške.
- **Windows Terminal UTF-8 Robustness**: Dodan automatski `sys.stdout.reconfigure(encoding='utf-8')` i očišćeni terminalni emojiji iz CLI naredbi.

## [v0.9.0] - 2026-09-18
### Added
- **Jev AI Decision Engine (Faza 22)**: Integracija Jev AI (typesafe/jev-1.13) via OpenRouter za donošenje odluka, s CRAG noise filterom za filtriranje irelevantnog konteksta.
- **kronos_jev_decide MCP Tool**: Novi MCP alat koji vanjskim agentima omogućuje delegiranje odluka Jev AI sustavu (35/35 testova).
- **OpenRouter Embeddings**: Podrška za `text-embedding-3-large` (3072 dim) embeddinge putem OpenRoutera.
- **Hardcore Resilience Suite**: Opsežni testovi otpornosti — adversarialni inputi, chaos network failure scenariji i live E2E (27/27 testova).
- **Pearlman Objection Skills**: `closing-easy-yes`, `objection-no-yet`, `objection-have-website` i `price-tourism` skillovi za detekciju i obradu prigovora (Faze 2-3).
- **CRM Closing Section**: Sekcija za zatvaranje u CRM profilu + detekcija spola interlokutora.

### Changed
- **Embedding Model Upgrade**: Prelazak na `text-embedding-004` za standardne embeddinge.
- **LLM Migracija**: `gemini-2.0-flash` → `gemini-2.5-flash`.

### Fixed
- **SemanticCache AttributeError**: Popravljen bug u semantičkom cacheu.
- **Test Database Isolation**: Testovi sada koriste izoliranu bazu putem `KRONOS_DATA_PATH` env varijable, bez diranja produkcijske baze.

## [v0.8.0-alpha] - 2026-06-08
### Added
- **Smart Context Engine (Faza 1)**: Semantičko podudaranje korisničkih upita sa registriranim skillovima te privremeno zaustavljanje izvršavanja radi korisničkog odobrenja (Human-in-the-loop).
- **Skill Manager**: Skener `SKILL.md` datoteka koji parsira YAML frontmatter, indeksira ih u SQLite bazu i generira vektorske embeddinge.
- **Approval System**: Mehanizam odobrenja s podrškom za sinkrono polling blokiranje niti izvršavanja dok korisnik ne riješi zahtjev.
- **FastAPI Endpoints**: Rute za dohvat i skeniranje skillova te pregled i rješavanje (odobravanje/odbijanje) zahtjeva za odobrenje.
- **Hard Tests**: Opsežan set testova (`test_skills_hard.py`) za provjeru rubnih slučajeva, timeouta, odbijanja i konkurentnosti.

### Fixed
- **Windows Logger Unicode Robustness**: Dodano hvatanje `UnicodeEncodeError` u logeru pri ispisu emojija na Windows konzolama koje nemaju UTF-8 podršku.
- **Dynamic Skill Threshold**: Uvedeno čitanje praga podudaranja iz okoline (`KRONOS_SKILL_THRESHOLD`) s optimalnim defaultom od `0.5` za stabilniji Gemini matching.

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
