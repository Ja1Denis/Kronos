# Trenutni Status Projekta (Kronos)
Datum: 2026-02-08 H2

## 🚀 Status: Faza 6 - DEFAULT STABLE (Cognitive Mastery)
Projekt je postavljen kao **Default Baseline** verzija (2026-02-09). Fokus je na stabilnosti i širenju znanja unutar ove arhitekture.

### 09.02.2026. (H0) - Autonomni Kustos (Curator)
- **Autonomous Curator (T025)**: Dovršen modul za samostalno održavanje baze znanja.
- **Duplicate Detection**: `curate --duplicates` pronalazi semantičke duplikate među odlukama (npr. "Koristimo SQLite" vs "Baza je SQLite").
- **Knowledge Mining**: `curate --refine` skenira nestrukturirane tekstove i predlaže nove strukturirane entitete (Odluke/Činjenice).
- **Historian Audit**: Integriran alat za provjeru konzistentnosti (`audit`).

### 09.02.2026. (H4) - Instant Search & Daemon Mode
- **Client-Server Architecture**: Uveden `start_kronos.ps1` i `ask_fast.ps1`.
- **Cold Start Elimination**: Pretraga se izvršava u <1s jer su AI modeli trajno učitani u memoriju servera.
- **Desktop Readiness**: Kreiran desktop prečac "Kronos Server" za pokretanje cijelog stacka.

### 09.02.2026. (H3) - Precision Tuning (Faza 7 Start)
- **Cross-Encoder Reranking (T027)**: Implementiran `BAAI/bge-reranker-base` model u `Oracle` pipeline.
    - Sustav sada uzima top 15 kandidata (3x limit) i re-rankira ih dubokom analizom konteksta.
    - Async preload osigurava nultu latenciju nakon prvog starta servera.
- **Benchmark**: Inicijalni rezulati (Recall@5 ~16.7%) ukazuju na potrebu za daljnjim finetuningom. Mehanizam je funkcionalan.

### 08.02.2026. (H2) - Implementacija Historiana i Contradiction Detection
- **Historian Module (T026)**: Implementirana detekcija semantičkih kontradikcija između novih unosa i postojećeg znanja. Koristi LLM za analizu konflikata.
- **Audit Command**: Dodana `kronos audit "tvrdnja"` komanda za brzu provjeru konzistentnosti.
- **Entity Semantic Indexing**: Librarian sada automatski indeksira entitete (odluke, činjenice) u vektorsku bazu (ChromaDB) paralelno s SQLite-om, omogućujući `Oracle`-u da ih pronađe putem semantičke pretrage.
- **Unified Retrieval**: Oracle `ask` metoda sada koristi 4-stage retrieval:
    1. Query Expansion (Topic/HyDE)
    2. Vector Search (Document Chunks)
    3. Vector Search (Entities Only - Boosted)
    4. Keyword Search (FTS5)
- **Bug Fixes**: Riješen problem s "utapanjem" entiteta u velikim chunkovima dokumenata dodavanjem dediciranog entity-only vektorskog upita.
- **Cleanup**: Očišćeni "zombi" procesi (Ingestor/Watcher) koji su ostali visiti u pozadini.

### 08.02.2026. - Evolucija u RAG Asistenta (Faza 5)
- **RAG Chat Implementation**: `chat` komanda sada koristi Gemini-2.0-flash za generiranje ljudskih odgovora na temelju pronađenih citata.
- **Live Sync (Auto-monitoring)**: Integriran Watcher u chat. Baza se automatski osvježava čim se spremi `.md` datoteka (debounce 2s).
- **Keyword Boost (Strict Mode)**: Znatno pojačana težina FTS pretrage. Tehnički pojmovi (poput "Live Sync") sada imaju prioritet nad općenitom vektorskom sličnošću.
- **SDK Migration**: Cijeli sustav prebačen na novi `google-genai` SDK (uklonjen Deprecation Warning).
- **UX Improvements**: Omogućeno scrollanje u Windows terminalu (buffer 5000 linija) i povećan prikaz odgovora na 1000 znakova.
- **Entity Recovery**: Implementirana bolja ekstrakcija ključnih riječi za pretragu entiteta (odluke, zadaci).

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
