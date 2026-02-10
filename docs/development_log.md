# Development Log - Kronos

### [2026-02-10] Faza 7: Stabilizacija (Context Budgeter) - COMPLETED
- **Cilj:** Optimizacija konteksta, smanjenje latencije i eliminacija DB grešaka.
- **Status:** ✅ Completed
- **Ključne promjene:**
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
