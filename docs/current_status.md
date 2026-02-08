# Trenutni Status Projekta (Kronos)
Datum: 2026-02-08 H2

## 🚀 Status: Faza 6 U Tijeku (Cognitive Mastery)
Projekt je tranziciji iz Faze 5 u **Fazu 6 (Cognitive Mastery)**, s fokusom na autonomiju i naprednu detekciju konzistentnosti.

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
- **Autonomous Curator**: Samostalno upravljanje životnim ciklusom informacija.
- **Precision Tuning**: Cilj 85% Recall.

### 📊 Statistika Baze:
- **Indeksirano datoteka**: ~2400 (uključujući testne projekte)
- **Ukupno chunkova**: ~14000
- **Ekstrahirano znanje**: Preko 10,000 entiteta.

### 🛠️ Tehnički Dug / Napomene:
- Riješen problem s prikazom `rich` panela na Windows CLI-u (prelazak na `print` za stabilnost).
