# Plan Projekta Kronos: Semantička Memorija

## 🏃 Faza 1: "Srednja Razina" (Infrastruktura)
Cilj: Postaviti osnovni pipeline za ingestion i retrieval (Hybrid Search).

- [ ] **T001: Environment Setup** <!-- id: 0 -->
    - [ ] Kreirati Python virtualno okruženje (`venv`).
    - [ ] Definirati `requirements.txt` (chromadb, sentence-transformers, sqlite-utils).
    - [ ] Kreirati osnovnu strukturu direktorija (`src/`, `data/`).

- [ ] **T002: Agent Ingestor (MVP)** <!-- id: 1 -->
    - [ ] Napisati skriptu `src/ingest.py`.
    - [ ] Implementirati čitanje `.md` datoteka (rekurzivno).
    - [ ] Dodati osnovni **chunking** (na razini paragrafa/headers).

- [ ] **T003: Vector Database Integration** <!-- id: 2 -->
    - [ ] Inicijalizirati lokalni **ChromaDB**.
    - [ ] Integrirati `sentence-transformers` (all-MiniLM-L6-v2) za embeddinge.
    - [ ] Spremiti prve chunkove u bazu.

- [ ] **T004: Agent Oracle (Retrieval)** <!-- id: 3 -->
    - [ ] Napisati skriptu `src/query.py`.
    - [ ] Implementirati semantičko pretraživanje (vektori).
    - [ ] Testirati query ("Kako X radi?") na lokalnim podacima.

## 🧠 Faza 2: "Hardcore Razina" (Pametna Ekstrakcija)
Cilj: Implementirati "Kronoraising" arhitekturu.

- [ ] **T005: Extraction Pipeline** <!-- id: 4 -->
    - [ ] Implementirati logiku za prepoznavanje entiteta (Regex/NLP).
    - [ ] Izdvojiti "Problem -> Solution" parove.
    - [ ] Strukturirati podatke u JSON.

- [ ] **T006: Hybrid Search** <!-- id: 5 -->
    - [ ] Dodati **SQLite FTS5** za keyword search.
    - [ ] Povezati rezultate s ChromaDB (Reranking).
    - [ ] Implementirati BM25 algoritam.

- [ ] **T007: CLI Sučelje** <!-- id: 6 -->
    - [ ] Kreirati user-friendly CLI (`kronos ask "pitanje"`).
    - [ ] Dodati opciju `--context` za ispis relevantnih fileova.
