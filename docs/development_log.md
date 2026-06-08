# Development Log - Kronos

### [2026-06-07] Faza 19: MCP Tasks & Streaming (v0.7.3) - COMPLETED 📦🤖⚡
- **Cilj:** Poboljšanje responzivnosti MCP alata uvođenjem asinkrone ingestije (Tasks) i SSE streaminga konteksta za kronos_query.
- **Status:** ✅ Completed (Na Git grani `feat/mcp-tasks-streaming`)
- **Ključne promjene:**
    - **Asinkroni `kronos_ingest`:** Alat više ne blokira klijenta. Odmah šalje zadatak u Job Queue i vraća `job_id`. Praćenje se obavlja preko `kronos_job_status`.
    - **Fino praćenje napretka:** Dodana podrška za `progress_callback` u `Ingestor.run` i `run_batch` koji računa postotak po datotekama i ažurira SQLite te emitira SSE događaje u stvarnom vremenu.
    - **Jedinstveni Worker:** MCP Server je spojen na punu klasu `Worker` iz `src/modules/worker.py` umjesto internog loopa.
    - **Streaming u `kronos_query`:** Ugrađen SSE stream u query alat koji u realnom vremenu emitira faze pretrage i postupno šalje chunkove/entitetet pretplatnicima na `/stream`.
    - **MCP Server Cards:** Kreiran standardizirani `mcp-server-card.json` i izložen kroz resurs `kronos://meta/card`.
    - **Windows Unicode Encoding:** Riješeni `UnicodeEncodeError` problemi kod printanja emojija na Windowsima u `server.py` i testovima.

### [2026-06-07] Faza 18: Self-RAG petlja & Migration Fix - COMPLETED 📦🤖⚡
- **Cilj:** Uvođenje evaluacijske petlje za samoispravak i nadopunu konteksta pomoću LLM-a, te ispravak SQLite migracije na postojećim bazama.
- **Status:** ✅ Completed (Na Git grani `feat/self-rag-loop`)
- **Ključne promjene:**
    - **Self-RAG Evaluacija:** `Oracle` modul provodi LLM evaluaciju primarno dohvaćenog konteksta. Ako je kontekst nedovoljan, LLM predlaže `RE-QUERY` s kojim se pokreće drugi krug pretraživanja, a rezultati se spajaju.
    - **MCP Alati:** Prošireni `kronos_query` i `kronos_search` s parametrom `self_rag` (default: `False`).
    - **SQLite Migracijski Fix:** Popravljeno dodavanje temporalnih stupaca u `graph_edges` na postojećim bazama izbjegavanjem SQLite greške ne-konstantnog defaulta.
    - **Testovi i Benchmark:** Stvoreni unit testovi `tests/test_self_rag.py` (3 mock scenarija) i skripta `tests/benchmark_self_rag.py` za analizu performansi dohvata.

### [2026-06-06] Faza 17: Temporal Knowledge Graph (Soft-delete & povijest) - COMPLETED 📦🕸️⚡
- **Cilj:** Uvođenje vremenskog praćenja (`valid_from`/`valid_to`) za čvorove i veze kako bi se uklonjeni elementi iz koda soft-deletali i filtrirali iz AI konteksta, uz zadržavanje povijesti.
- **Status:** ✅ Completed (Na Git grani `feat/temporal-knowledge-graph`)
- **Ključne promjene:**
    - **Temporalna SQLite shema:**
        - Tablica `graph_nodes` više nema PRIMARY KEY na `node_id`, već se koristi `id INTEGER PRIMARY KEY AUTOINCREMENT` i indeks na `node_id`. Dodani su stupci `valid_from` i `valid_to`.
        - Tablica `graph_edges` je proširena sa stupcima `valid_from` i `valid_to`.
        - Uvedena je automatska migracija za postojeće baze koja rekreira `graph_nodes` i dodaje stupce u `graph_edges` bez gubitka podataka.
    - **Temporalna add_node / add_edge logika (Python):**
        - Prilikom unosa, ako se sadržaj ili metapodaci čvora/veze razlikuju od postojećeg aktivnog zapisa, stari zapis se soft-deleta (`valid_to = NOW`), a novi umeće. Ako su isti, unos se preskače.
    - **Aktivno filtriranje upita (Python & Rust):**
        - Svi SQL SELECT upiti u `disk_graph.py` i u C++ PyO3 modulu `rust_engine_v3/src/lib.rs` (BFS traversals, paths, subgraphs) nadograđeni su s filterom `valid_to IS NULL` kako bi AI klijenti dobivali isključivo trenutačno važeći codebase kontekst.
    - **Inkrementalna sinkronizacija (Soft-delete):**
        - Skripta `build_knowledge_graph.py` sada prati sve čvorove i veze viđene tijekom trenutnog skeniranja.
        - Na kraju skeniranja, svi aktivni elementi projekta koji nisu viđeni u novom skenu automatski se soft-deletaju postavljanjem `valid_to = CURRENT_TIMESTAMP`.

### [2026-06-06] Faza 16: sqlite-vec integracija (Hibridna konsolidacija) - COMPLETED 📦⚡
- **Cilj:** Zamjena glomazne i nestabilne ChromaDB baze s ultra-brzom i laganom SQLite ekstenzijom `sqlite-vec`.
- **Status:** ✅ Completed (Na Git grani `feat/sqlite-vec-migration`)
- **Ključne promjene:**
    - **Instalacija i Učitavanje:** Integrirana `sqlite-vec` biblioteka (v0.1.9) u virtualno okruženje na Windows 11. Ekstenzija se učitava dinamički prilikom svake SQLite konekcije u `Librarian._get_sqlite_conn()`.
    - **Tablični Dizajn:** 
        - Kreirana tablica `vec_metadata` za pohranu tekstova dokumenta i metapodataka u JSON formatu.
        - Kreirana virtualna tablica `vec_items` za brzu vektorsku pretragu (dimenzija 3072 za Gemini Embeddings).
    - **Vektorski Adapter (`Oracle` & `Librarian`):**
        - Redizajniran `safe_upsert` za slanje i pohranu vektora izravno u SQLite bazu.
        - Redizajniran `_retrieve_candidates` u `Oracle` klasi: zamijenjen `resilient_vector_query` s SQL MATCH upitom preko `sqlite-vec` ekstenzije. Rezultati se mapiraju u stari Chroma format, čime su spriječeni svi breaking-changes u ostatku koda.
    - **Pouzdanost i Testiranje:** 
        - Svi testovi prebačeni s ChromaDB-a na `sqlite-vec` (ažuriran `tests/test_chromadb_health.py`).
        - Svih **34 integracijskih i unit testova uspješno prolazi** s 0 grešaka.
        - Eliminirane race condition greške ("database locked") jer se svi podaci nalaze u jednoj datoteci.

### [2026-03-03] Faza 15: Kronos Command Center (Dashboard & SSE) - COMPLETED 🎨
- **Cilj:** Vizualizacija statusa i memorije Kronos sustava u stvarnom vremenu kroz lokalni web preglednik.
- **Grana:** `feat/kronos-command-center`
- **Status:** ✅ Completed (Inicijalna verzija)
- **Ključne promjene:**
    - **Dashboard Setup:** Kreiran `/dashboard` direktorij korištenjem Vite-a s Premium Glassmorphism dizajnom.
    - **Back-end Integracija:** 
        - Ažuriran `server.py` FastAPI s dodanim `CORSMiddleware` za nesmetanu komunikaciju.
        - Dodano posluživanje statičkih datoteka (`StaticFiles`) na `/dashboard` ruti.
    - **Real-time Eventi:** Povezan `EventSource` (SSE) na klijentu (`main.js`) za dohvat sistemskih logova i ažuriranja poslova u pregledu.
    - **Baza Znanja (Knowledge Base View):**
        - Implementiran pregled i tablica za iteraciju kroz stvoreno znanje.
        - Povezani gumbi za dinamičko "fetchiranje" Entiteta (`/entities`) i Odluka (`/decisions`) iz SQLite-a.
        - UI navigacija prebacuje poglede bez potrebe za reloadanjem stranice.

### [2026-02-19] Faza 14: Rust & Hybrid Graph Optimization (v0.6.2-rust-hybrid) - COMPLETED 🦀⚡
- **Cilj:** Povećanje performansi pretrage grafa znanja korištenjem Rust-a uz zadržavanje fleksibilnosti Python-a kroz hibridnu arhitekturu.
- **Status:** ✅ v0.6.2 Released
- **Ključne promjene:**
    - **Hibridna Arhitektura ("Smart Router"):**
        - Implementiran inteligentni router u `DiskKnowledgeGraph` koji na temelju procjene težine upita (fanout * dubina) bira motor.
        - **Mali upiti:** Python ostaje primarni motor zbog 0ms FFI overhead-a kod jednostavnih SQLite poziva.
        - **Teški upiti (Weight > 15):** Rust preuzima kontrolu koristeći optimizirane **Recursive CTE** SQL upite na disku.
    - **Selective Fetch (Hydration):**
        - Riješen problem sporog stvaranja kompleksnih Python objekata unutar Rust-a.
        - Rust sada vraća isključivo listu ID-ova čvorova (`Vec<String>`).
        - Python vrši "batch hydration" koristeći SQL `IN` klauzulu za dohvat punih podataka u jednom koraku.
    - **Rust Performance (Release Build):**
        - Uspješno postavljen build proces s `--release` optimizacijama.
        - SQLite perzistencija unutar Rust-a osigurava minimalnu latenciju pri povezivanju.
    - **Stabilizacija PyO3 0.20:**
        - Kôd prilagođen stabilnoj verziji PyO3 0.20 bez korištenja depreciranih/eksperimentalnih API-ja.
- **Problemi i Rješenja:**
    - **Problem:** FFI pozivi su skuplji od samog SQL upita za male datasetove.
    - **Rješenje:** Uvođenje heuristike procjene težine (Smart Router) koja čuva Rust za "maratonske" pretrage.
    - **Problem:** PyO3 `_bound` API i poteškoće s `PyObject` konverzijom.
    - **Rješenje:** Redizajn komunikacije na razini ID-ova (minimalistički interface).

### [2026-02-14] Faza 13: Multi-Agent & Scaling (v0.5.1-multi-agent) - COMPLETED 🛡️
- **Cilj:** Omogućiti istovremeni rad više AI agenata/IDE prozora nad istom bazom znanja i skalabilnu ingestiju velikih workspaceova.
- **Status:** ✅ v0.5.1 Released
- **Ključne promjene:**
    - **Multi-Agent Architecture (SSE):** 
        - Dodana puna podrška za **Server-Sent Events (SSE)** transport u `mcp_server.py` (`--sse` flag).
        - Implementiran `src/mcp_bridge.py` koji omogućuje klijentima koji podržavaju samo `stdio` (poput Antigravity/Cursor) da se spoje na centralni SSE server, eliminirajući problem zaključane baze (`database is locked`).
        - Kreiran `start_kronos.ps1` za pokretanje centralnog servera u pozadini.
    - **Scalable Ingestion (Job Worker Fix):**
        - Popravljen kritični bug u `JobManager` workeru koji je sprječavao pokretanje asinkronih poslova. Worker sada ispravno koristi `Ingestor` klasu.
        - Uspješno provedena ingestija cijelog `ai-test-project` workspacea (**668 datoteka, ~25k chunkova**).
    - **Database Stability:**
        - Omogućen **WAL (Write-Ahead Logging)** mode za SQLite na Windowsima radi bolje konkurentnosti.
        - Dodan alat `kronos_reinit_oracle` za oporavak veze s bazom bez restartanja servera.
    - **Efficiency Validation:**
        - Potvrđena ušteda od **90.3% tokena** na kompleksnim upitima (npr. CroStem arhitektura) u odnosu na raw context.

### [2026-02-13] Faza 12: MCP Stability & Windows Integration (v0.3.0-mcp-stable) - COMPLETED 🛡️
- **Cilj:** Rješavanje kritičnih problema s MCP komunikacijom na Windowsima i sprječavanje timeouta pri inicijalizaciji.
- **Status:** ✅ v0.3.0 Released & Tagged
- **Ključne promjene:**
    - **Agresivni stdout štit:** Implementirana OS-level `os.dup2` redirekcija koja nasilno preusmjerava sistemski FD 1 (stdout) na FD 2 (stderr). Ovo sprječava C/Rust biblioteke (poput ChromaDB) da zagađuju JSON-RPC kanal nasumičnim ispisima.
    - **Lazy Background Initialization:** Oracle, Librarian i ChromaDB inicijalizacija je prebačena u pozadinski thread. MCP handshake sada prolazi trenutno, sprečavajući "EOF while reading" i timeout greške u IDE-u.
    - **ContextItem robustnost:** Dodano `metadata` polje u `ContextItem` dataclass. Riješen `TypeError` koji je nastajao pri obradi rezultata iz Oraclea.
    - **Safe Print (Monkey-patching):** Globalni `print` zamijenjen sigurnim wrapperom koji uvijek koristi `stderr`, sprječavajući rekurzivne greške pri logiranju izuzetaka.
    - **Cleanup:** Maknuti suvišni `redirect_stdout` wrapperi iz alata, čime je kôd očišćen i ubrzan.

### [2026-02-13] Faza 11: System Robustness & Testing (v2.2.0-robust) - COMPLETED 🛡️
- **Cilj:** Implementacija zaštitnih slojeva protiv nevaljanih upita, retry logike za stabilnost API-ja i pune testne pokrivenosti.
- **Status:** ✅ v2.2.0-robust Released
- **Ključne promjene:**
    - **FTS Search Robustness (Librarian):** Implementirana `_escape_fts_token` metoda koja sanitizira upite. Riješen problem s `sqlite3.OperationalError` kod pretrage koda koji sadrži zagrade, navodnike i crtice.
    - **Hibridni Pretraživač:** Dodan `AND` -> `OR` fallback mehanizam u FTS pretragu. Ako striktan `AND` podudaranje ne vrati rezultate, sustav automatski pokušava širi `OR` upit.
    - **Retry Logic (Tenacity):** Implementiran `resilient_vector_query` wrapper oko ChromaDB poziva. Svi vektorski upiti sada imaju 3 pokušaja s `exponential backoff` (1s-5s) za otpornost na asinkrone database lockove.
    - **System Metrics:** Uvedena `SystemMetrics` klasa za praćenje performansi i stabilnosti u realnom vremenu. Prati se: `health_score`, `fts_failure_rate`, `vector_failure_rate` i ukupni volumen upita.
    - **API Monitoring:** Ažuriran `/health` endpoint u `server.py` koji sada vraća detaljan status sustava.
    - **Test Coverage:** Kreiran `tests/` paket s Unit testovima za sanitizaciju, Integration testovima za API i Load testovima za provjeru skalabilnosti.
    - **Automation:** Razvijen `run_all_tests.ps1` za brzu validaciju cijelog sustava jednim klikom.

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
