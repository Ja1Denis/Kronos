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

- [x] **T013: Event Sourcing Arhitektura** <!-- id: 12 -->
    - [x] Učiniti `archive.jsonl` primarnim izvorom istine (Source of Truth).
    - [x] Kreirati `rebuild_from_archive.py` skriptu za regeneraciju SQLite/ChromaDB iz JSONL-a.
    - [x] Testirati full rebuild i validirati integritet.
    - [x] Dokumentirati event schema (insert/update/delete eventi).

- [x] **T014: Entity-First Retrieval** <!-- id: 13 -->
    - [x] Modificirati `Oracle.ask()` da prvo vraća strukturirane objekte (Decision/Fact/Task).
    - [x] Tek nakon objekata prikazati "evidence chunks" kao supporting materijal.
    - [x] Dodati type-aware boosting (ako upit sadrži "odluka" → prioritiziraj Decision entitete).
    - [x] Implementirati "Entity Card" formatiranje u CLI outputu.

- [x] **T015: Temporal History Query** <!-- id: 14 -->
    - [x] Proširiti `Oracle` da vraća povijest promjena za odluke ("prije" vs "sada").
    - [x] Dodati `--history` flag u CLI za prikaz evolucije odluka.
    - [x] Pametna detekcija upita o promjenama ("kako se mijenjao cilj?").
    - [x] API endpoint `/decisions/{id}/history` za timeline.

- [x] **T016: Benchmark & Evaluation Suite** <!-- id: 15 -->
    - [x] Kreirati `eval/` folder s 20+ test pitanja.
    - [x] Skripta za mjerenje: (a) Recall@K, (b) Context Tokens, (c) Latency.
    - [x] Usporedba: raw file dump vs Kronos retrieval.
    - [x] Generiranje Markdown reporta s rezultatima.
    - [x] Integracija u CI (pytest ili standalone).

- [x] **T017: Active Memory CLI (save/promote)** <!-- id: 16 -->
    - [x] `kronos save "tekst" --as decision/fact/task` - brzi unos zapisa.
    - [x] `kronos promote CHUNK_ID --as decision` - pretvaranje rezultata pretrage u trajni zapis.
    - [x] Interaktivni wizard ako korisnik ne specificira tip.
    - [x] Validacija duplikata prije spremanja.

- [x] **T018: Hybrid Search Pipeline (Hardening)** <!-- id: 17 -->
    - [x] Refaktorirati Oracle da koristi 3-stage pipeline kao default:
        1. Keyword filter (FTS5/BM25) nad naslovima i sažecima.
        2. Dense retrieval (ChromaDB) nad top-N kandidata.
        3. Reranking nad top-K finalista.
    - [x] A/B testiranje stare vs nove pipeline logike.
    - [x] Konfigurabilni parametri (N, K) kroz config.

- [x] **T019: Multi-Project Dashboard** <!-- id: 18 -->
    - [x] CLI komanda `kronos projects` - lista svih projekata s statistikama.
    - [x] `kronos project [ime] --stats` - detalji o pojedinom projektu.
    - [x] Web UI (opcionalno, FastAPI + HTMX) za vizualizaciju znanja.

## 🪄 Faza 5: "Symbiosis" (Generative Intelligence)
Cilj: Implementirati napredne kognitivne funkcije koristeći LLM (Gemini) za generiranje hipoteza i kontekstualno razumijevanje.

- [x] **T020: HyDE Implementation (Hypothetical Embeddings)** <!-- id: 19 -->
    - [x] Kreirati `Hypothesizer` klasu (koristeći Gemini API).
    - [x] Implementirati flow: Upit -> LLM -> Lažni Odgovor -> Vektorizacija -> Pretraga.
    - [x] Dodati cacheiranje generiranih hipoteza (JSON cache).
    - [x] Evaluacija poboljšanja Recall-a (HyDE radi ispravno na "backup" primjeru).

- [x] **T021: Contextual Retrieval (Small-to-Big)** <!-- id: 20 -->
    - [x] Implementirati `Contextualizer` modul za proširenje konteksta.
    - [x] Integrirati u `Oracle` za top rezultate.
    - [x] Koristiti file-reading metodu umjesto reindeksiranja (efikasnije).

- [x] **T022: Query Expansion & Multi-Search** <!-- id: 21 -->
    - [x] Nadograditi `Hypothesizer` s metodom `expand_query`.
    - [x] Ažurirati `Oracle.ask` za multi-query retrieval.
    - [x] Implementirati RRF (Reciprocal Rank Fusion) za spajanje rezultata.

- [x] **T023: Semantic Clustering & Auto-Tagging** <!-- id: 22 -->
    - [x] Automatsko pronalaženje imena tema (LLM Topic Discovery).
    - [x] Auto-tagging relevantnih chunkova (LLM/Vector match).
    - [x] Korisnička CLI naredba `analyze`.
    - [x] Vizualizacija mapa znanja (Knowledge Graph basic).

- [x] **T024: RAG Chat & UX Finalization** <!-- id: 23 -->
    - [x] Integrirati Gemini za generiranje ljudskih odgovora (RAG).
    - [x] Live Sync podrška unutar Chat CLI-ja (pozadinski Watcher).
    - [x] Popravljeni Windows CLI problemi (Scroll buffer, Window size).
    - [x] Implementirano "Strict Keyword Boost" za tehničke pojmove u Oracleu.

## 🚀 Faza 6: "Cognitive Mastery" (Advanced Autonomy)
Cilj: Puna autonomija u upravljanju znanjem i postizanje vrhunske preciznosti sustava.

- [ ] **T025: Autonomous Agent Curator** <!-- id: 24 -->
    - [ ] Razvoj samostalne klasifikacije (Decision/Task/Fact) bez korisničkog unosa.
    - [ ] Pametna detekcija duplikata i auto-merging sličnih informacija.
    - [ ] Proaktivno predlaganje ažuriranja zastarjelih informacija.

- [ ] **T026: Knowledge Timeline (Historian)** <!-- id: 25 -->
    - [x] Implementirati `--history` view koji vizualno prikazuje evoluciju dokumenta.
    - [x] Detekcija kontradikcija između starih odluka i novih unosa.
    - [x] "Promote & Deprecate" sustav za upravljanje životnim ciklusom znanja.

- [ ] **T027: Precision Tuning (85% Recall Target)** <!-- id: 26 -->
    - [ ] Implementacija Cross-Encodera za napredni Reranking (Stage 3).
    - [ ] Finetuning embeddinga ili prelazak na veće modele za bolju semantiku.
    - [ ] Validacija Recall@5 metrike na proširenom testnom skupu.
