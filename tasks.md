# Plan Projekta Kronos: Semantička Memorija

## 🏃 Faza 1: "Srednja Razina" (Infrastruktura)
Cilj: Postaviti osnovni pipeline za ingestion i retrieval (Hybrid Search).

- [x] **T001: Environment Setup** <!-- id: 0 -->
    - [x] Kreirati Python virtualno okruženje (`venv`).
    - [x] Definirati `requirements.txt` (chromadb, sentence-transformers, sqlite-utils).
    - [x] Kreirati osnovnu strukturu direktorija (`src/`, `data/`).

- [x] **T002: Agent Ingestor (MVP)** <!-- id: 1 -->
    - [x] Napisati skriptu `src/ingest.py`.
    - [x] Implementirati čitanje `.md` datoteka (rekurzivno).
    - [x] Dodati osnovni **chunking** (na razini paragrafa/headers).

- [x] **T003: Vector Database Integration** <!-- id: 2 -->
    - [x] Inicijalizirati lokalni **ChromaDB**.
    - [x] Integrirati `sentence-transformers` (all-MiniLM-L6-v2) za embeddinge.
    - [x] Spremiti prve chunkove u bazu.

- [x] **T004: Agent Oracle (Retrieval)** <!-- id: 3 -->
    - [x] Napisati skriptu `src/query.py`.
    - [x] Implementirati semantičko pretraživanje (vektori).
    - [x] Testirati query ("Kako X radi?") na lokalnim podacima.

## 🧠 Faza 2: "Hardcore Razina" (Pametna Ekstrakcija)
Cilj: Implementirati "Kronoraising" arhitekturu.

- [x] **T005: Extraction Pipeline** <!-- id: 4 -->
    - [x] Implementirati logiku za prepoznavanje entiteta (Regex/NLP).
    - [x] Izdvojiti "Problem -> Solution" parove.
    - [x] Strukturirati podatke u JSON.

- [x] **T006: Hybrid Search** <!-- id: 5 -->
    - [x] Dodati **SQLite FTS5** za keyword search.
    - [x] Povezati rezultate s ChromaDB (Reranking).
    - [x] Implementirati BM25 algoritam.

- [x] **T007: CLI Sučelje** <!-- id: 6 -->
    - [x] Kreirati user-friendly CLI (`kronos ask "pitanje"`).
    - [x] Dodati opciju `--context` za ispis relevantnih fileova.

- [x] **T008: Daemon Mode (Server)** <!-- id: 7 -->
    - [x] Implementirati FastAPI server.
    - [x] Dodati REST endpointe (/ingest, /query, /stats).
    - [x] Omogućiti JSON output za AI agente.
    - [x] Implementirati File Watcher za automatsko reindeksiranje.

- [x] **T009: Project Awareness & Chat** <!-- id: 8 -->
    - [x] Implementirati `project` tagiranje u bazi podataka.
    - [x] Migrirati postojeće podatke.
    - [x] Dodati interaktivni `chat` mod u CLI.
    - [x] Implementirati pametno filtriranje po projektima.

## 🚀 Faza 3: "God Mode" (Advanced Features)
Cilj: Pretvoriti Kronosa u aktivnog sugovornika i alat za upravljanje znanjem.

- [x] **T010: Temporal Truth (Vrijeme i Odluke)** <!-- id: 9 -->
    - [x] Proširiti shemu za `valid_from`, `valid_to`, `superseded_by`.
    - [x] Implementirati logiku za detekciju kontradikcija (Foundations).
    - [ ] API za "ratifikaciju" odluka.

- [x] **T011: Robustness & Safety** <!-- id: 10 -->
    - [x] Implementirati **Debounce** za watcher.
    - [ ] Dodati **Backup** komandu (`kronos backup`).

- [x] **T012: Connectivity (MCP)** <!-- id: 11 -->
    - [x] Implementirati **Model Context Protocol (MCP)** server.
    - [x] Omogućiti korištenje Kronosa kao alata u Claude/Gemini desktop aplikacijama.
