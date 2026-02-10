# Trenutni Status Projekta (Kronos)
Datum: 2026-02-10 H2

## 🚀 Status: Faza 7 - STABILITY & CONTEXT (Completed)
Projekt je stabiliziran i spreman za produkciju. Riješeni su problemi s konkurentnošću i optimiziran je dohvat konteksta.

### [2026-02-10] Faza 7: Context Budgeter & Stability (COMPLETED)
- **Status:** ✅ Stable (Thread-safe, 600ms latency under load)
- **Ključna postignuća:**
    - **Singleton Oracle + Thread Lock:** Eliminirane `database is locked` greške kod paralelnih upita.
    - **Context Budgeter:** Dinamičko upravljanje tokenima (Light/Auto/Extra).
    - **The Three Corpses (T034):** Potpuna debug podrška (Code + Diffs + Logs).
    - **Stress Test:** 30 istovremenih read/write operacija prošlo bez greške.

### ⚠️ Poznati Problemi / TODO
- (Next) Faza 8: Autonomy & Job Queue (za asinkrone zadatke).

---

### [2026-02-09] Faza 6 - ARCHIVED (Cognitive Mastery)
Projekt je postavljen kao **Default Baseline** verzija (2026-02-09). Fokus je bio na stabilnosti i širenju znanja.

### 09.02.2026. (H0) - Autonomni Kustos (Curator)
- **Autonomous Curator (T025)**: Dovršen modul za samostalno održavanje baze znanja.
- **Duplicate Detection**: `curate --duplicates` pronalazi semantičke duplikate.
- **Knowledge Mining**: `curate --refine` skenira nestrukturirane tekstove.
- **Historian Audit**: Integriran alat za provjeru konzistentnosti (`audit`).

### 09.02.2026. (H4) - Instant Search & Daemon Mode
- **Client-Server Architecture**: Uveden `start_kronos.ps1` i `ask_fast.ps1`.
- **Cold Start Elimination**: Pretraga <1s.
- **Desktop Readiness**: Kreiran desktop prečac.

### 09.02.2026. (H3) - Precision Tuning
- **Cross-Encoder Reranking (T027)**: Integriran `bge-reranker-base`.

### 08.02.2026. (H2) - Implementacija Historiana
- **Event Sourcing**: Potpuni integritet podataka.
- **3-Stage Hybrid Search**: Keyword -> Vector -> Reranking.

### 💎 Postignuća Faze 4 (Završeno):
- **Event Sourcing**: Potpuni integritet podataka kroz `archive.jsonl`.
- **3-Stage Hybrid Search**: Keyword -> Vector -> Reranking pipeline.
- **Entity-First Retrieval**: Prioritet strukturiranim objektima (odluke, zadaci).
- **Temporal History**: Praćenje evolucije odluka.
- **Benchmark Suite**: Sustav za mjerenje točnosti (70.5% Recall@5).

### 🚧 Trenutni Fokus (Faza 6):
- **Precision Tuning**: Implementacija Cross-Encodera i finetuning embeddinga (T027).
- **RAG Evaluation**: Proširenje benchmark skripte.

### 📊 Statistika Baze:
- **Indeksirano datoteka**: ~2400 (uključujući testne projekte)
- **Ukupno chunkova**: ~14000
- **Ekstrahirano znanje**: Preko 10,000 entiteta.

### 🛠️ Tehnički Dug / Napomene:
- Riješen problem s prikazom `rich` panela na Windows CLI-u (prelazak na `print` za stabilnost).
