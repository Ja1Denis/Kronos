# Faza 8: Autonomy & Job Queue (The Agentic Leap) - ROBUST PLAN

**Cilj:** Transformirati Kronos iz pasivnog RAG alata u **proaktivnog, asinkronog suradnika** s naglaskom na stabilnost, perzistenciju i standarde (MCP).

---

## 🏗️ Arhitektura: In-Process Job Queue (Persistent)
Odabran je **Single-Process Model** s SQLite backendom za jobove.

1.  **API Layer (FastAPI)**: Prima zahtjeve -> Piše u `jobs.db` -> Notificira Workera.
2.  **Job Persistence (`jobs.db`)**: Tablica `jobs` (id, type, status, priority, params, result, progress, created_at, started_at, finished_at).
3.  **Worker Thread (Background)**:
    - Vrti se u petlji (uzima `pending` jobove iz DB).
    - Koristi `Singleton Oracle` (pod lockom).
    - Ažurira status i progress u DB.
    - Sluša `shutdown_event` za sigurno gašenje.

---

## 📅 Sprint Plan

### Sprint 1: Temelj Job Queue-a (Persistence & Safety)
*Cilj: Job Queue radi, preživljava restart i ne gubi podatke.*

*   **T038: Job Manager Core & Persistence**
    *   [x] Kreirati `JobManager` klasu i `jobs.db` (SQLite).
    *   [x] Implementirati metode: `submit_job`, `get_job`, `update_progress`.
    *   [x] Auto-cleanup starih poslova (>7 dana).
*   **T039: Async API Endpoints**
    *   [x] `POST /jobs` (submit), `GET /jobs/{id}` (status), `DELETE /jobs/{id}` (cancel).
    *   [x] `T039.1`: **Cancellation Logic**: Worker provjerava `cancelled` flag svake iteracije.
*   **T040: Worker Thread & Graceful Shutdown**
    *   [x] **Worker Loop**: Uzima jobove iz DB (priority order).
    *   [x] `T040.1`: **Graceful Shutdown**: Na SIGTERM/Ctrl+C, Worker završava trenutni batch ili radi clean exit.

### Sprint 2: Watcher Intelligence & Evaluation (Batching & Benchmarks)
*Cilj: Watcher ne guši sustav, a mi mjerimo kvalitetu.*

*   **T040.2: Watcher Batch Logic**
    *   [x] Implementirati `pending_changes` set. Ne kreirati job za svaku promjenu, već batchati.
    *   [x] Provjera: Ako već postoji `pending` reindex job, samo dodaj fileove u njega (unutar debounce intervala).
*   **T047: Evaluation Metrics Dashboard**
    *   [x] Pratiti metrike: `job_success_rate`, `avg_latency` (dodano u `kronos jobs`).
*   **T048: Benchmark Runner CLI**
    *   [x] Alat za regresijsko testiranje (`kronos evaluate`).

### [2026-02-10] Faza 8 - Sprint 4: Proactive Features (COMPLETED)
- **Cilj:** Implementirati proaktivnu analizu i sustav notifikacija.
- **Status:** ✅ Completed & Stress Tested
- **Ključne promjene:**
    - **Notification Manager:** SSE endpoint `/stream` za real-time komunikaciju.
    - **Proactive Analyst:** Automatska analiza datoteka nakon ingesta.
    - **Smart Historian:** Detekcija kontradikcija pomoću Gemini 2.0 modela.

### [2026-02-10] Faza 8 - Sprint 3: Agentic Tools (COMPLETED)
*Cilj: LLM razumije i koristi Kronos samostalno.*

*   **T041: MCP-Compatible Tool Manifest**
    *   [x] Definirati alate prema **Model Context Protocol** (MCP) standardu.
    *   [x] Implemetirani alati: `kronos_search`, `kronos_stats`, `kronos_decisions`, `kronos_ingest`.
*   **T042: Auto-Routing Logic**
    *   [x] Heuristika: Alati imaju dugačke i precizne opise kako bi LLM znao kada ih koristiti (npr. "Korisno za dugotrajne operacije").

### Sprint 4: Proactive Features (COMPLETED)
*Cilj: Kronos se sam javlja.*

*   **T044: Context Monitor**
    *   [x] Implementiran `ProactiveAnalyst` koji analizira ingestirane datoteke.
    *   [x] Integracija s **Historianom** za detekciju kontradikcija u realnom vremenu.
    *   [x] Koristi `gemini-2.0-flash` za inteligentno rasuđivanje.
*   **T046: Notification System (SSE)**
    *   [x] `GET /stream`: Server-Sent Events za notifikacije.
    *   [x] Real-time ažuriranja o statusu poslova i proaktivne sugestije.
    *   [x] Podrška za više simultanih klijenata.

---

## 📋 Definition of Done (DoD) za svaki task
1.  **Unit Test**: Pokriva logiku (npr. prioriteti u queue).
2.  **Integration Test**: End-to-end flow (Submit -> Worker -> Db Update -> Result).
3.  **Manual Test**: Scenarij provjeren ručno (npr. Ctrl+C usred ingesta).
4.  **Metrics**: Nema regresije u performansama.
