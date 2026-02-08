# Development Log - Kronos

## [2026-02-08] - Faza 6: "Cognitive Mastery" (Historian & Contradiction)

### Dodano:
- **`src/modules/historian.py`**: Novi modul za semantičku analizu kontradikcija. Koristi LLM (Gemini) za usporedbu novih tvrdnji s postojećim "Decision" i "Fact" entitetima.
- **`audit` CLI komanda**: Omogućuje korisniku ručnu provjeru konzistentnosti (`kronos audit "tvrdnja"`).
- **Dual Vector Search**: Nadograđen `Oracle` da izvodi dvije paralelne pretrage:
    1. Standardni "chunk" search (dokumenti).
    2. "Entity-focused" search (samo odluke/činjenice) s boostanim score-om. Ovo rješava problem gdje su bitni entiteti bili nadjačani velikim dokumentima.
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
