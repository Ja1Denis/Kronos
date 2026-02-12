# Kronos Pointer System - Detaljni Task Plan

***

## FAZA 0: PRIPREMA I CLEANUP (prije bilo kakvog kodiranja)
 nakon svakog taska napravi test

### Task 0.1: Backup i Safety Net
- [ ] Kreiraj Git branch: `feature/pointer-system`
- [ ] Commitaj trenutno stanje: "Baseline before pointer refactor"
- [ ] Kreiraj backup folder: `kronos_backup_20260211/`
- [ ] Kopiraj cijeli `src/` folder u backup
- [ ] Dokumentiraj trenutne endpoint-e koji rade (curl testovi)
- [ ] Zapiši sve poznate bugove u `KNOWN_ISSUES.md`
- [ ] testaj da li server radi

### Task 0.2: Čišćenje Indexa (riješi metadata=None problem)
- [x] Zaustavi Kronos server
- [x] Pronađi gdje se čuva vektorska baza (ChromaDB folder ili SQLite)
- [x] Obrisi cijeli index: `rm -rf data/chromadb/` ili `del data\chroma.db`
- [x] Provjeri da li postoje orphaned lock fajlovi (`.lock`, `.pid`)
- [x] Obrisi cache foldere: `__pycache__/`, `.pytest_cache/`
- [x] Restartuj i verifikuj da server startuje čist

### Task 0.3: Environment Setup
- [x] Instaliraj dependencies koji će trebati:
  - `pip install psutil` (za process management)
  - `pip install filelock` (za file locking)
  - `pip install python-dotenv` (ako već nemaš)
- [x] Kreiraj `.env` fajl sa config varijablama:
  ```
  MAX_POINTERS=5
  POINTER_TOKEN_BUDGET=100
  CHUNK_TOKEN_BUDGET=4000
  ENABLE_POINTER_MODE=true
  ```
- [x] Dodaj `.env` u `.gitignore`

### Task 0.4: Create CODING_GUIDELINES.md
- [x] Kreiraj fajl: `docs/CODING_GUIDELINES.md`
- [x] Dokumentiraj obvezne obrasce (Defense in Depth, Forbidden Patterns).
- [x] Sadržaj prema specifikaciji (Type Check First, Validate Before Use, Handle Errors Gracefully, Never Trust Data).

***

## FAZA 1: TYPE DEFINITIONS (Data strukture)

### Task 1.1: Kreiraj novi modul za tipove
- [x] Kreiraj fajl: `src/modules/types.py`
- [x] Definiraj `@dataclass Pointer` sa svim poljima:
  - `file_path: str`
  - `section: str`
  - `line_range: tuple[int, int]`
  - `keywords: list[str]`
  - `confidence: float`
  - `last_modified: str`
  - `content_hash: str` (SHA256)
  - `indexed_at: str` (ISO timestamp)
- [x] Dodaj metodu: `to_context() -> str` (formatira za LLM)
- [x] Dodaj metodu: `is_stale() -> bool` (provjerava timestamp)
- [x] Dodaj metodu: `verify_content() -> bool` (provjerava hash)
- [x] Dodaj unit test: `test_pointer_serialization()`

### Task 1.2: Extend SearchResult Type
- [x] Otvori postojeći tip `SearchResult` (ili kreiraj u `types.py`)
- [x] Dodaj field: `type: Literal["pointer", "chunk", "exact"]`
- [x] Dodaj optional field: `pointer: Pointer | None`
- [x] Dodaj optional field: `content: str | None`
- [x] Dodaj optional field: `metadata: dict | None`
- [x] Provjeri da sve postojeće funkcije koje koriste `SearchResult` još kompajliraju
- [x] Dodaj unit test: `test_search_result_types()`

### Task 1.3: Query Type Enum
- [x] Definiraj enum u `types.py`:
  ```python
  class QueryType(Enum):
      LOOKUP = "lookup"
      AGGREGATION = "aggregation"
      SEMANTIC = "semantic"
  ```
- [x] Dodaj docstring sa primjerima za svaki tip

***

## FAZA 2: DEFENSIVE INGEST (Spriječi metadata=None)

### Task 2.1: Audit Existing Ingest Pipeline
- [x] Pronađi SVE mjesta gdje se poziva `vector_db.add()` ili slično (identificiran `upsert` u `ingestor.py`, `librarian.py`, `rebuild_from_archive.py`)
- [x] Zapiši sve fajlove i linije gdje se dodaju dokumenti
- [x] Provjeri: Da li svaki `add()` poziv setira metadata? (Zasad da, ali bez linija)
- [x] Pronađi: Gdje se događa chunking (splitting dokumenata) (`ingestor.py: _chunk_content`)
- [x] Zapiši: Koji field-ovi se stavljaju u metadata trenutno (`source`, `project`, `filename`, `type`, `entity_type`, `entity_id`)

### Task 2.2: Metadata Validation Layer
- [x] Kreiraj funkciju: `validate_metadata(metadata: dict) -> bool` (u `src/utils/metadata_helper.py`)
- [x] Provjeri obavezna polja:
  - `source` (file path) mora postojati
  - `source` mora biti validan path (provjeri sa `os.path.exists()`)
  - `start_line` i `end_line` moraju biti int
  - `last_modified` mora biti validan ISO timestamp
- [x] Ako validacija faila: Log error + zaustavi insert
- [x] Dodaj unit test: `test_metadata_validation_rejects_none()`
- [x] Dodaj unit test: `test_metadata_validation_rejects_invalid_path()`

### Task 2.3: Wrap All Vector DB Inserts
- [x] Task 2.3a: Pronađi sve `vector_db.add()` (i sl.) pozive koristeći grep/search
- [x] Task 2.3b: Dokumentiraj svaku lokaciju poziva i pripadajući kontekst
- [x] Task 2.3c: Identificiraj pattern-e (jesu li svi pozivi slični ili ima custom logike?)
- [x] Task 2.3d: Kreiraj `safe_add_document(content, metadata)` wrapper u `src/modules/oracle.py` (kao `safe_upsert`)
- [x] Task 2.3e: Zamijeni pozive jedan po jedan (uz testiranje nakon svakog)
- [x] Task 2.3f: Verificiraj da nijedan poziv nije propušten (ponovni grep)
- [x] Dodaj timestamp: `metadata['indexed_at'] = datetime.now().isoformat()`
- [x] Dodaj content hash: `metadata['content_hash'] = hashlib.sha256(...).hexdigest()`
- [x] Log svaki insert: `"✅ Indexed: {metadata['source']}"`

### Task 2.4: Handle Chunk Rejections
- [x] Pronađi gdje se dešava "chunk_limit_exceeded" reject
- [x] Implementiraj retries ili skip s logom
- [x] Osiguraj da se preostali chunkovi i dalje procesiraju

## FAZA 2.5: VALIDATION & SECURITY HARDENING
### Task 2.5.1: Path Traversal Prevention
- [x] Kreiraj funkciju: `is_safe_path(file_path: str, allowed_root: str) -> bool`
- [x] Provjeri da path ne sadrži: `..`, absolute paths izvan root-a, simlinkove izvan root-a, null byte.
- [x] Implementiraj unit testove za malicious input.

### Task 2.5.2: Metadata Type Enforcement
- [x] Kreiraj funkciju: `enforce_metadata_types(metadata: Any) -> dict | None`
- [x] Implementiraj agresivne tipovske provjere (Check 1 do Check 5 iz specifikacije).
- [x] Implementiraj unit testove za `None`, krivu strukturu, negativne linije.

### Task 2.5.3: Line Range Validation
- [x] Kreiraj funkciju: `validate_line_range(start: int, end: int, file_path: str) -> tuple[bool, str]`
- [x] Provjeri: `start >= 0`, `end > start`, limit range na 10,000 linija (DoS prevention).
- [x] Validacija protiv stvarne duljine datoteke.

***

## FAZA 3: ORACLE REFACTOR (Decision Logic)

### Task 3.1: Query Type Detection
- [x] Task 3.1a: Izgradi testni dataset od 50 primjera upita (labeliranih) (u `tests/data/query_dataset.json`)
- [x] Task 3.1b: Heuristika za detekciju (keywords: "popis", "koliko", "list", "who", "summary")
- [x] Task 3.1c: Unit test: `test_query_type_detection` (Accuracy check) -> 84% postignuto.
- [x] Task 3.1d: Dodaj `semantic` fallback ako nijedan keyword ne matcha
- [x] Task 3.1e: Podrška za hrvatski i engleski jezik u istom parseru

### Task 3.2: Confidence Thresholding (Lookup branch)
- [x] Postavi konstante: `HIGH_CONFIDENCE = 0.75`, `MEDIUM_CONFIDENCE = 0.4`
- [x] Implementiraj check u `ask()`
- [x] Log: `"🎯 High match found (Loading full context)"`
- [x] Log: `"📍 Partial match found (Generating Pointer)"`

### Task 3.3: Aggregation Branch Logic
- [x] Ako je `QueryType.AGGREGATION`: Uzmi prvih N rezultata (limit 20)
- [x] Ako ih ima > 5, automatski ih sve pretvori u Pointere
- [x] Log: `"📊 Aggregation query: Bundling {len(results)} pointers"`

### Task 3.5: Keyword Extraction (Filtered)
- [x] Implementiraj `extract_keywords(query: str) -> List[str]` u `Oracle`
- [x] Filtriraj stopwords (u, na, i, the, is, for...)
- [x] Uzmi top 3-5 riječi za pointer metadata

### Task 3.6: Backward Compatibility Support
- [x] Osiguraj da `ask()` i dalje vraća `entities` i `chunks` keys radi CLI-ja
- [x] Dodaj novi key `pointers` u return dict
- [x] Dodaj `query_type` u return dict za debugging

### Task 3.7: Oracle decision tree overhaul
- [x] Task 3.7a: Refaktoriraj `ask()` metodu da koristi grananje
- [x] Task 3.7b: Implementiraj `_candidate_to_pointer` helper
- [x] Task 3.7c: Integriraj deduplikaciju kandidata prije odlučivanja
- [x] Task 3.7d: Integriraj HyDE samo za `SEMANTIC` upite
- [x] Task 3.7e: Integriraj Query Expansion limitirano na `SEMANTIC` upite
- [x] Task 3.7f: Verificiraj da deduplikacija radi preko više proširenih upita
- [x] Task 3.7g: Dodaj error handling za slučajeve kad pretraga ne vrati ništa
- [x] Task 3.7h: Osiguraj backward compatibility return formata

## FAZA 3.8: ORACLE DEFENSIVE PROGRAMMING
### Task 3.8.1: Null-Safe Result Classification
- [x] Implementiraj pre-check za prazne rezultate.
- [x] Try-except wrap za `result['score']` s fallbackom na 0.0.
- [x] Unit testovi za `score: None`, `score: 'invalid'`.

### Task 3.8.2: Pointer Generation Error Handling
- [x] Wrap cijeli pointer creation u `Oracle.ask()` u try-except.
- [x] Implementiraj skip-and-continue logiku za neispravne kandidate.
- [x] Logiranje summary-ja: "Created X pointers, Y failed".

### Task 3.8.3: Oracle.ask() Fallback Chain
- [x] Implementiraj `try-except` oko cijele `ask()` metode.
- [x] Dodaj `empty_response` fallback.
- [x] Dodaj `error_response` fallback s jasnim error porukama.

***

## FAZA 4: RESPONSIVE LLM (Antigravity Upgrade)
### Task 4.1: build_pointer_response()
- [x] Kreiraj funkciju: `build_pointer_response(pointers: list[Pointer]) -> dict`
- [x] Format output prema specifikaciji.
- [x] Dodaj token estimate: `estimated_tokens: int`

### Task 4.2: build_mixed_response()
- [x] Definiraj instrukcije za LLM model kako tretirati mixed response (`docs/PROMPT_GUIDELINES_POINTERS.md`).
- [x] Ažuriraj Antigravity system prompt s uputama za pointere.
- [x] Format output prema specifikaciji.

### Task 4.3: build_chunk_response() (update existing)
- [x] Dodaj field: `"type": "chunk_response"`.

***

## FAZA 5: CONTEXT BUDGETER UPDATE
### Task 5.1: Priority Queue Logic
- [x] Refaktoriraj `allocate()`: Primi mixed list, sortiraj Pointere prvo.
- [x] Phase 1: Dodaj SVE pointere.
- [x] Phase 2: Dodaj high-confidence chunk-ove dok ima budgeta.
- [x] Ako chunk ne stane: Convert to pointer.

### Task 5.2: Logging Improvements
- [x] Logiranje dodavanja i odbacivanja (REJECTED/ADDED [pointer/chunk]).
- [x] Summary log na kraju: "Budget: X/Y tokens | Pointers: A | Chunks: B".

## FAZA 5.5: BUDGETER ACCOUNTING SAFETY
### Task 5.5.1: Token Estimation Bounds
- [x] Dodaj bounds checking u `estimate_tokens()`.
- [x] Implementiraj safety margin (+20%) i capping na 100k tokena.
- [x] Testovi za None/Huge inpute.

### Task 5.5.2: Budget Tracking Audit
- [x] Implementiraj audit log u `allocate()` metodi.
- [x] Dodaj paranoidni `assert` check nakon svake alokacije.
- [x] Verificiraj da `total_estimated == budget_used`.

***

## FAZA 6: NEW ENDPOINT - /fetch_exact
### Task 6.1: Define Request Schema [DONE]
### Task 6.2: Circular Reference Tracker [DONE]
### Task 6.3: File Locking Helper [DONE]

## FAZA 6.6: FILE ACCESS HARDENING
### Task 6.6.1: File Locking with Timeout
- [x] Implementiraj `read_file_safe()` s timeoutom i lockingom (msvcrt/fcntl).
- [x] Bounds check protiv stvarnog broja linija unutar locka.
- [x] Detaljan error reporting (permission, encoding, not found).

### Task 6.6.2: Content Hash Verification s Graceful Degradation
- [x] Provjera hasha pri `fetch_exact` pozivu.
- [x] Ako hash ne matchira, vrati sadržaj uz `warning: stale_pointer`.

***

## FAZA 9.9: EDGE CASE TEST SUITE
### Task 9.9.1: Malformed Input Tests (Security fuzzer) [DONE]
### Task 9.9.2: Unicode/Croatian Encoding Tests [DONE]
### Task 9.9.3: Concurrency Stress Test [DONE]

***

## COMPLETION CHECKLIST
- [ ] Sve unit tests pass
- [ ] Documentation complete
- [ ] Zero circular request infinite loops
- [ ] Token usage reduced by >50%