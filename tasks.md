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
    - [x] API za "ratifikaciju" odluka.

- [x] **T011: Robustness & Safety** <!-- id: 10 -->
    - [x] Implementirati **Debounce** za watcher.
    - [x] Dodati **Backup** komandu (`kronos backup`).

- [x] **T012: Connectivity (MCP)** <!-- id: 11 -->
    - [x] Implementirati **Model Context Protocol (MCP)** server.
    - [x] Omogućiti korištenje Kronosa kao alata u Claude/Gemini desktop aplikacijama.

## 🌌 Faza 4: "Evolution" (Kronos 2.0)
Cilj: Pretvoriti Kronos iz "još jednog RAG-a" u pravi Semantički Operativni Sustav.

- [ ] **T013: Event Sourcing Arhitektura** <!-- id: 12 -->
    - [ ] Učiniti `archive.jsonl` primarnim izvorom istine (Source of Truth).
    - [ ] Kreirati `rebuild_from_archive.py` skriptu za regeneraciju SQLite/ChromaDB iz JSONL-a.
    - [ ] Testirati full rebuild i validirati integritet.
    - [ ] Dokumentirati event schema (insert/update/delete eventi).

- [ ] **T014: Entity-First Retrieval** <!-- id: 13 -->
    - [ ] Modificirati `Oracle.ask()` da prvo vraća strukturirane objekte (Decision/Fact/Task).
    - [ ] Tek nakon objekata prikazati "evidence chunks" kao supporting materijal.
    - [ ] Dodati type-aware boosting (ako upit sadrži "odluka" → prioritiziraj Decision entitete).
    - [ ] Implementirati "Entity Card" formatiranje u CLI outputu.

- [ ] **T015: Temporal History Query** <!-- id: 14 -->
    - [ ] Proširiti `Oracle` da vraća povijest promjena za odluke ("prije" vs "sada").
    - [ ] Dodati `--history` flag u CLI za prikaz evolucije odluka.
    - [ ] Pametna detekcija upita o promjenama ("kako se mijenjao cilj?").
    - [ ] API endpoint `/decisions/{id}/history` za timeline.

- [ ] **T016: Benchmark & Evaluation Suite** <!-- id: 15 -->
    - [ ] Kreirati `eval/` folder s 20+ test pitanja.
    - [ ] Skripta za mjerenje: (a) Recall@K, (b) Context Tokens, (c) Latency.
    - [ ] Usporedba: raw file dump vs Kronos retrieval.
    - [ ] Generiranje Markdown reporta s rezultatima.
    - [ ] Integracija u CI (pytest ili standalone).

- [ ] **T017: Active Memory CLI (save/promote)** <!-- id: 16 -->
    - [ ] `kronos save "tekst" --as decision/fact/task` - brzi unos zapisa.
    - [ ] `kronos promote CHUNK_ID --as decision` - pretvaranje rezultata pretrage u trajni zapis.
    - [ ] Interaktivni wizard ako korisnik ne specificira tip.
    - [ ] Validacija duplikata prije spremanja.

- [ ] **T018: Hybrid Search Pipeline (Hardening)** <!-- id: 17 -->
    - [ ] Refaktorirati Oracle da koristi 3-stage pipeline kao default:
        1. Keyword filter (FTS5/BM25) nad naslovima i sažecima.
        2. Dense retrieval (ChromaDB) nad top-N kandidata.
        3. Reranking nad top-K finalista.
    - [ ] A/B testiranje stare vs nove pipeline logike.
    - [ ] Konfigurabilni parametri (N, K) kroz config.

- [ ] **T019: Multi-Project Dashboard** <!-- id: 18 -->
    - [ ] CLI komanda `kronos projects` - lista svih projekata s statistikama.
    - [ ] `kronos project [ime] --stats` - detalji o pojedinom projektu.
    - [ ] Web UI (opcionalno, FastAPI + HTMX) za vizualizaciju znanja.
