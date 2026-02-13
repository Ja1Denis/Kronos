# Faza 9: Hybrid Intelligence & Speed (The Efficiency Leap)

**Cilj:** Dramatično ubrzati Kronos uvođenjem "brze staze" (Short-circuiting), optimizacijom hibridne pretrage i inteligentnim upravljanjem resursima. Kronos ne smije biti spor za jednostavna pitanja.

---

## 🏗️ Koncept: "Fast Path" Arhitektura
Uvodimo slojeviti pristup pretraživanju:
1.  **L0: Regex/Literal Cache** (0-10ms): Odmah vraća rezultate za emailove, ključeve i fiksne stringove.
2.  **L1: Optimized FTS (Full Text Search)** (10-50ms): Brza tekstualna pretraga (SQLite). Ako je score visoka, preskače se AI.
3.  **L2: Semantic Vector Search** (100-500ms): ChromaDB pretraga za koncepte i značenje.
4.  **L3: Reranker Mastery** (1-2s): Samo za kompleksna pitanja gdje L1 i L2 nisu sigurni.

---

## 📅 Sprint Plan

### Sprint 1: Short-Circuit & Fast Path
*Cilj: Rezultati za emailove i ID-eve moraju biti instant.*

*   **T051: Regex & Literal Fast-Path**
    *   Detekcija emailadresa, URL-ova i ID-eva u upitu.
    *   Ako je detektiran "Hard Key", pokreće se isključivo super-brzi `grep` mode.
    *   **Short-circuit**: Ako L0 nađe 100% pogodak, prekida se daljnja AI obrada.
*   **T052: FTS-First Hybrid Scaling**
    *   Prebacivanje prioriteta: FTS (Keyword) pretraga se pokreće prva.
    *   Implementacija "Confidence Score": Ako FTS vrati rezultat sa score-om > 0.9, preskače se Reranker.
*   **T053: Singleton Model Offloading**
    *   Osigurati da se AI modeli ne učitavaju ako je upit riješen u "Fast Path" fazi (Power saving/Latency reduction).

### Sprint 2: Lifecycle & Resource Management
*Cilj: Eliminacija zombi procesa i stabilizacija memorije.*

*   **T054: Zombie Watchdog Implementation**
    *   Skripta unutar servera koja prati "viseće" pretrage i gasi thread-ove koji traju predugo (>10s).
    *   Auto-cleanup `jobs.db` od "stuck" poslova pri restartu.
*   **T055: Query Result Caching (LRU)**
    *   Implementacija memorijskog cache-a za identične upite.
    *   Vrijeme trajanja cache-a se resetira pri svakoj novoj ingestiji (Cache Invalidation).

### Sprint 3: Detailed Metrics & Audit
*Cilj: Korisnik mora znati zašto je neka pretraga trajala.*

*   **T056: Latency Breakdown API**
    *   Ažuriranje `/query` odgovora da uključuje `latency_breakdown`:
        *   `fts_time`, `vector_time`, `rerank_time`, `total_time`.
*   **T057: "Thinking" Log in CLI**
    *   `ask_fast.ps1` treba prikazati: "Našao sam točan pogodak u kôdu, preskačem AI analizu radi brzine."

---

## 📋 Definition of Done (DoD)
1.  **Speed Bench**: Upit za email adresu mora završiti za < 150ms (trenutno > 2s).
2.  **Zero Zombi**: Nakon 100 paralelnih upita, broj Python procesa mora ostati jednak 1.
3.  **Accuracy Check**: Uvođenje Fast-Path-a ne smije smanjiti Recall@5 na benchmark testovima.
