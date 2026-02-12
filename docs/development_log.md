# Development Log - Kronos

### [2026-02-12] Faza 10: Pointer System (v2.3.0-gold-pointer) - COMPLETED ✅
- **Cilj:** Implementacija inteligentnog "Just-in-Time" dohvaćanja konteksta i stabilizacija masovne ingestije.
- **Status:** ✅ v2.3.0 Released & Merged to Master

- **Ključne promjene:**
    - **Cleanup (T0.2):** Zaustavljen server, obrisana ChromaDB i SQLite baze, očišćeni cache-ovi. Sustav starta s "nula" podataka kako bi se eliminirali `metadata=None` problemi.
    - **Dependencies (T0.3):** Instalirani `psutil`, `filelock` i `python-dotenv`.
    - **Configuration:** Kreiran `.env` za upravljanje budgetima pointera i chunkova.
    - **Planning:** Detaljno razrađen `kronos_ne_nalazi_podatke.md` plan s 12 faza.
    - **Type Definitions (Faza 1):** Definirani ključni objekti za novi sustav. `Pointer` sada sadrži `line_range`, `content_hash` i `to_context()` metodu za LLM. Uveden `QueryType` enum za razlikovanje lookup i aggregation upita.
    - **Encoding Intelligence:** Implementiran `detect_encoding()` u `file_helper.py` koristeći BOM signatures i fallback detekciju. Riješen kritični `UnicodeDecodeError` kod PowerShell-generated datoteka.
    - **Noise Reduction:** Ingestor sada filtrira `.git`, `__pycache__`, i specifične interne datoteke (`handoff*.md`, `faza*.md`).
    - **Pointer Integration:** `AntigravityAgent` orkestriran s `PointerResolverom`. Sustav sada radi puni ciklus: Query -> Pointers -> Selective Fetch -> Final Response.
    - **Massive Ingest Automation:** `ingest_everything.py` automatizira kompletan workflow (Kill -> Wipe -> Ingest All).
    - **Production Readiness:** `LLMClient` prebačen na realni Gemini API. `README.md` ažuriran s detaljnim Token Efficiency izračunima.

### [2026-02-11] Faza 9: Rust Integration (v2.1.0-beta-rust) - RELEASED 🧪
- **Cilj:** Implementacija ultrabrzog Rust pretraživača (Fast Path) i službeni Beta izlazak.
- **Status:** ✅ v2.1.0-beta-rust Released

- **Ključne promjene:**
    - **Rust Engine (`kronos_core`):** Kreiran visoko-performansni modul u Rustu (PyO3). Implementiran `PrefixTrie` i `exact_index` (HashMap) za trenutno podudaranje nizova.
    - **Fast Path (L0/L1):** Oracle sada prvo konzultira Rust modul. Ako pronađe točno podudaranje ili prefiks s visokim pouzdanjem (>= 0.9), preskače vektorsku i AI pretragu. Odziv: **< 1ms**.
    - **PowerShell UX:** Ažurirani `reset_kronos.ps1` i `ask_fast.ps1` s vizualnim "spinnerima" i brojačima vremena za profesionalniji dojam i bolju povratnu informaciju.
    - **Knowledge Expansion:** `Ingestor` sada podržava moderne web formate: `.js`, `.jsx`, `.tsx`, `.html`. 
    - **Build & Integration:** Uspješno postavljen `maturin` build proces s release optimizacijama. Modul je integriran u Python codebase s elegantnim fallbackom.


- **Cilj:** Vektorizacija i ingestija svih projekata u `ai-test-project` workspace-u.
- **Status:** ✅ Completed
- **Ključne promjene:**
    - **Full Workspace Indexing:** Ingestirano 13 projekata: `cortex-api`, `cortex-search-extracted`, `CroStem`, `crostem_rs`, `CroStem_v012`, `cro_stem`, `kronos`, `SerbStem`, `Skills`, `SlovStem`, `WordpressPlugin`, `WordpressPublisher`, `zip_test`.
    - **Stats Boost:**
        - Datoteka: ~22,000
        - Chunkova: ~49,000
        - Entiteta: ~13,500
 ### FAZA 1: TYPE DEFINITIONS (Completed)
- Kreiran `types.py` i `tests/test_types.py`.
- Definirane bazične strukture za Pointer System.

### FAZA 2: DEFENSIVE INGEST (Completed)
- Kreiran `src/utils/metadata_helper.py` za centraliziranu validaciju i obogaćivanje metapodataka.
- Implementiran `safe_upsert` u `Oracle` i `Librarian`.
- `Ingestor` sada podržava line-aware chunking (svaki chunk zna svoj start/end line).

### FAZA 3: ORACLE REFACTOR (Completed)
- Implementirana heuristika za detekciju tipa upita (`LOOKUP`, `AGGREGATION`, `SEMANTIC`).
- Testirano na datasetu od 50 upita (Točnost: 84%).
- Implementiran glavni decision tree u `Oracle.ask()`. Sustav sada inteligentno odlučuje hoće li vratiti cijeli chunk (High Confidence) ili samo Pointer (Medium Confidence / Aggregation).

### [2026-02-12] - Security Hardening & Pointer Architecture Finalization
### Dodano:
- **Phase 2.5: Validation & Security Hardening**: Implementirana `is_safe_path`, `enforce_metadata_types` i `validate_line_range`. Sustav je sada imun na Path Traversal i DoS napade.
- **Phase 3.8: Oracle Defensive Programming**: Oracle je postao "robustan". Svi ključni procesi (`ask()`, `_candidate_to_pointer`) su umotani u try-except blokove s fallback mehanizmima.
- **Phase 4: Response Builders**: Dodani specijalizirani Response Builderi (`pointer_response`, `mixed_response`, `chunk_response`).
- **Phase 5.5: Budgeter Accounting Safety**: Context Budgeter je dobio audit log i paranoidne provjere alokacije. Procjena tokena sada uključuje safety margin i caps.
- **Phase 6.6: File Access Hardening**: Implementiran `/fetch_exact` endpoint u serveru. Korištenje `read_file_safe` s OS-level file lockingom (msvcrt/fcntl).
- **Phase 9.9: Edge Case Test Suite**: Postignuta 100% prolaznost na testovima za Malicious Inputs, Croatian Encoding i Concurrency Stress Test.

### Poboljšano:
- **Section Title Extraction**: Oracle sada inteligentno izvlači naslove sekcija iz Markdowna (#) za prikaz u pointerima.
- **Pointer Clustering**: Implementirano grupiranje pointera po direktoriju radi sprječavanja redundancije u kontekstu.
- **Documentation**: Kreiran `docs/CODING_GUIDELINES.md` kao standard za "Defense in Depth" programiranje.

---

### [2026-02-10] Faza 8 - Sprint 2: Intelligence & Evaluation (COMPLETED)
- **Cilj:** Optimizacija Watcher-a i uvođenje metrika kvalitete.
- **Status:** ✅ Completed
- **Ključne promjene:**
    - **Watcher Batching (T040.2):** Smanjen pritisak na bazu kroz grupiranje datoteka (`ingest_batch`) s debounce-om od 5s.
    - **Jobs CLI & Metrics (T047):** Praćenje `success_rate` i latencije kroz novu naredbu `kronos jobs`.
    - **Evaluate CLI (T048):** Integriran Benchmark sustav izravno u glavne komande (`kronos evaluate`).

### [2026-02-10] Faza 8 - Sprint 1: Job Queue & Persistence (COMPLETED)
- **Cilj:** Implementacija asinkronog sustava za upravljanje zadacima i priprema za autonomiju.
- **Status:** ✅ Completed
- **Ključne promjene:**
    - **Single-Process Job Queue (T038):**
        - Implementiran `JobManager` s SQLite backendom (`data/jobs.db`).
        - Podržava prioritete, status (`pending`, `running`, `completed`, `failed`) i `json` parametre.
        - Potpuna perzistencija - queue preživljava restart servera.
    - **Async API (T039):**
        - Dodani endpointi: `POST /jobs`, `GET /jobs/{id}`, `DELETE /jobs/{id}`.
        - Omogućuje klijentima (npr. VS Code ekstenzija) da šalju dugotrajne zadatke bez blokiranja.
    - **Worker Thread (T040):**
        - Implementiran pozadinski `Worker` (Daemon Thread).
        - Vrti se u petlji unutar serverskog procesa (dijeli memoriju s Oracle-om).
        - Graceful Shutdown: Na `Ctrl+C` ili stop signal, worker završava trenutni korak i gasi se čisto.
        - Podržava `ingest` jobove (asinkrona indeksacija).

### [2026-02-10] Faza 7: Stabilizacija (Context Budgeter) - COMPLETED
- **Cilj:** Optimizacija konteksta, smanjenje latencije i eliminacija DB grešaka.
- **Status:** ✅ Completed
- **Ključne promjene:**
    - [2026-02-10] **Faza 8 Završena**: Kronos je postao asinkroni agent s proaktivnim mogućnostima. Implementiran Job Queue, MCP, SSE notifikacije i inteligentna analiza kontradikcija. Stabilnost potvrđena kroz "The Inquisitor" stres test.
    - [2026-02-10] **Sprint 3 (CPM)**: MCP alatnica (7 alata) verificirana.
    - [2026-02-10] **Sprint 1 & 2**: Job Queue stabiliziran, batching Watcher funkcionalan.
    - [2026-02-09] **Faza 7**: Migracija na FastAPI + Singleton Oracle. Riješeni concurrency problemi.
    - **Context Budgeter:** Implementiran algoritam za dinamičko upravljanje tokenima (Light/Normal/Extra profili).
    - **Singleton Oracle:** Riješen problem s paralelnim pristupom ChromaDB-u (global threading lock).
    - **The Three Corpses (T034):**
        - **Code:** Snippeti oko stack trace-a.
        - **Diffs:** Prioritet za nedavno mijenjane datoteke.
        - **Logs:** Automatsko uvlačenje zadnjih 30 linija iz sistemskog loga (`logs/*.log`).
    - **Stres Test (Realistični Scenarij):**
        - 30 istovremenih Read/Write operacija (2 Editora, 2 Dev Agenta, 1 Debugger).
        - **Rezultat:** 100% Success Rate (0 grešaka), 622ms prosječna latencija.
        - **Zaključak:** Kronos je sada thread-safe i spreman za produkciju.

### [2026-02-09] Faza 7: Context Budgeter - Initial Setup...:
- **T028-T031: Context Budgeter Core**:
    - Kreiran `ContextComposer` (src/modules/context_budgeter.py) za pametno upravljanje kontekstom.
    - Implementiran **Greedy Algorithm** za popunjavanje budžeta (4000 tokena) s prioritetima: Cursor > Entities > Chunks.
    - Uvedeni limiti: Global (4000), File (3 chunka/900 tokena), Entity (800 tokena).
    - **Entity One-liners**: Entiteti se sada formatiraju kao sažeti jednolinijski opisi radi uštede prostora.
- **API Update**: `/query` endpoint sada vraća optimizirani `context` string umjesto sirovih rezultata.
- **CLI Update**: `ask_fast.ps1` ažuriran da podržava:
    - Slanje `CursorContext` i `CurrentFilePath` parametara.
    - Prikaz formatiranog konteksta i audit loga (potrošnja tokena, odbijeni kandidati).
- **T032-T034: Debug Repro Pack**:
    - **Stack Trace Parser**: `src/utils/stack_parser.py` izvlači putanje datoteka i linije iz error logova.
    - **Debug Mode**: Ako API primi `stack_trace`, automatski aktivira "Trace Anchors" mehanizam.
    - **The Three Corpses (Partial)**:
        - **Code**: Kronos čita ±5 linija oko svake greške u trace-u i dodaje ih u kontekst (Priority: 0.95).
        - **Diffs**: Ako je datoteka iz trace-a modificirana u zadnjih sat vremena, dobiva oznaku `[RECENTLY MODIFIED]` i boost prioriteta.
    - **CLI Support**: `ask_fast.ps1 -TraceFile "error.log"` šalje sadržaj loga serveru na analizu.
    - **Optimization**: Proveden "Clean Rebuild" baze (ChromaDB + SQLite) radi rješavanja problema s korumpiranim indeksima. Uveden Singleton Oracle pattern.

## [2026-02-09] - Baseline Freeze: Kronos v2.0.0-evolution
### Odluka:
- **Verzija Kronosa (Faza 6) se službeno postavlja kao DEFAULTNA verzija za budući rad.**
- Cilj: Osigurati stabilan temelj memorije prije daljnjih eksperimentalnih faza.

## [2026-02-09] - UX & Speed Optimization: Client-Server Architecture
### Dodano:
- **Kronos Server (FastAPI)**: Implementirana puna podrška za stalno pokrenut server (Daemon Mode). AI modeli se učitavaju samo jednom pri startu servera.
- **`ask_fast.ps1`**: Ultra-brza CLI klijentska skripta koja komunicira s API-jem. Latencija pretrage smanjena s 30s na <1s (Cold Start eliminiran).
- **`start_kronos.ps1`**: Pametni orkestrator koji pokreće server u pozadini, čeka "health check" potvrdu i javlja spremnost sustava.
- **Desktop Shortcut "Kronos Server"**: Kreiran prečac na radnoj površini za pokretanje sustava jednim klikom.

### Poboljšano:
- **Cross-Encoder Reranking (T027)**: Implementiran `BAAI/bge-reranker-base` za dubinsko rerankiranje top 15-20 rezultata. Značajno poboljšava preciznost na dvosmislenim upitima.
- **Async Model Preload**: Server sada učitava teške modele pri pokretanju, omogućujući trenutnu dostupnost za sve klijente.
- **Smart HyDE**: Optimizirana logika koja aktivira HyDE samo za kratke (<5 riječi) i nejasne upite. Default pretraga je sada instantna (<100ms).
- **SQLite Timeout**: Povećan timeout na 30s za `Librarian` konekciju kako bi se spriječile "database locked" greške tijekom Live Synca.

### Poboljšano (Infrastruktura):
- **Stabilnost**: Watcher i user queries sada mogu koegzistirati bez rušenja baze.
- **Performance**: Smanjena latencija za tipične use-caseove isključivanjem nepotrebnog HyDE-a.

---

## [2026-02-08] - Faza 6: "Cognitive Mastery" (Historian & Contradiction)

### Dodano:
- **`src/modules/historian.py`**: Novi modul za semantičku analizu kontradikcija. Koristi LLM (Gemini) za usporedbu novih tvrdnji s postojećim "Decision" i "Fact" entitetima.
- **`audit` CLI komanda**: Omogućuje korisniku ručnu provjeru konzistentnosti (`kronos audit "tvrdnja"`).
- **Unified Retrieval**: Oracle `ask` metoda sada koristi 4-stage retrieval:
    1. Query Expansion (Topic/HyDE)
    2. Vector Search (Document Chunks)
    3. Vector Search (Entities Only - Boosted)
    4. Keyword Search (FTS5)
- **Autonomous Curator (T025)**: Proširen `Curator` modul s metodama `identify_duplicates()` i `refine_knowledge()`. Omogućuje:
    - Semantičku detekciju duplikata među entitetima.
    - Ekstrakciju novih strukturiranih informacija iz nestrukturiranih tekstova.
- **CLI Updates**: Dodana komanda `curate` s opcijama `--duplicates` i `--refine`.
- **ChromaDB Entity Indexing**: `Librarian.save_entity` i `Ingestor` sada automatski indeksiraju entitete u ChromaDB, omogućujući njihovo pronalaženje putem vektorske pretrage (ne samo keyword search).

### Poboljšano:
- **Testiranje**: Dodan `test_historian.py` za validaciju detekcije kontradikcija.
- **Cleanup**: Implementirana skripta za čišćenje "zombi" procesa (Python/Ingestor) koji su preostali od dugotrajnog rada.

### Popravci (Bugfixes):
- **Oracle Query Logic**: Ispravljen `where` clause u ChromaDB upitima. Zamijenjen implicitni `AND` (dict merge) s eksplicitnim `$and` operatorom koji ChromaDB zahtijeva.
- **Entity Visibility**: Riješen problem gdje se odluke nisu pojavljivale u pretrazi ako nisu imale točan keyword match. Sada se koriste semantički embeddingi.

---

## [2026-02-08] - Faza 5 Start: "Symbiosis" Planning

### Kontekst:
- Kreće implementacija **Generative Intelligence** značajki (HyDE, Query Expansion).
- Cilj je podići **Recall@5** s trenutnih 70.5% na >85%.

### Dovršeno (Faza 5):
- **T020: HyDE Implementation**: Integracija Gemini API-ja (v2.0-flash) za generiranje hipoteza.
- **T022: Query Expansion**: Paralelna generacija varijacija upita.
- **Live Sync**: Integracija `Watcher` modula izravno u `chat` CLI. Kronos sada automatski re-ingestira promjene u `.md` datotekama tijekom chata.
- **Optimization**: Uveden `ThreadPoolExecutor` za paralelno procesiranje sub-upita.

### Promjene (U tijeku):
- **T021: Contextual Retrieval**: Poboljšanje `Ingestor`-a (parent references).

### Poboljšano:
- **Optimization (Search Latency)**: U `Oracle.ask` uvedena paralelna obrada (`ThreadPoolExecutor`) za HyDE i Query Expansion. Višestruki LLM pozivi sada idu istovremeno.
- **Hypothesizer Thread-Safety**: Dodan `threading.Lock` za perzistentni JSON cache.

### Popravci (Bugfixes):
- **CLI Rendering**: Zamijenjen `rich.Panel` s običnim `print` ispisom u `ask` i `chat` komandama zbog problema s prikazom na Windows terminalu.
- **Project Detection**: Poboljšana logika za automatsko prepoznavanje projekta iz upita ("što je cilj *kronosa*?").
- **Search Fallback**: Implementiran automatski fallback na globalnu pretragu ako specifični projekt ne vrati rezultate.

---

## [2026-02-08] - Faza 4: "Evolution" Implementation

### Dodano:
- **`src/rebuild_from_archive.py`**: Skripta za rekonstrukciju baze iz `archive.jsonl`. Podržava batch obradu za brzinu.
- **`src/benchmark.py`**: Sustav za evaluaciju performansi pretrage (Recall@5, Latency).
- **`run_chat.bat` & `create_shortcut.ps1`**: Alat za kreiranje Desktop prečaca za brzi pristup chatu.
- **`Librarian.save_entity`**: Metoda za ručni unos znanja.

### Poticaji i Promjene:
- **`Oracle.ask`**: Refaktoriran u 3-stage pipeline. Uveden hibridni score (vector sličnost + keyword boost 0.3).
- **`CLI`**:
    - Dodana komanda `rebuild` za oporavak baze.
    - Dodana komanda `history` za vizualizaciju timelinea odluka.
    - Dodana komanda `benchmark` za pokretanje testova.
    - Dodana komanda `save` za interaktivni unos.
    - Dodana komanda `projects` za multi-project dashboard.
    - Ažuriran prikaz entiteta ("Entity Cards").

### Popravci (Bugfixes):
- Ispravljen `TypeError` u CLI-u kod prikaza entiteta bez `source` metapodatka (ručni unosi).
- Optimiziran `rebuild` proces korištenjem SQLite transaction batchinga.
- Riješen problem s dupliciranim ID-evima u ChromaDB-u tijekom rekonstrukcije.

### Infrastruktura:
- Instalirana biblioteka `rfc3987` u venv radi podrške za JSON Schema validaciju.
- Ažuriran `tasks.md` - Faza 4 označena kao 100% dovršena.
