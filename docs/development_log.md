# Development Log - Kronos

## [2026-02-08] - Faza 5 Start: "Symbiosis" Planning

### Kontekst:
- Kreće implementacija **Generative Intelligence** značajki (HyDE, Query Expansion).
- Cilj je podići **Recall@5** s trenutnih 70.5% na >85%.

### Promjene (Planirano):
- **T020: HyDE Implementation**: Integracija Gemini API-ja za generiranje hipotetskih dokumanata prije vektorske pretrage.
- **T021: Contextual Retrieval**: Poboljšanje `Ingestor`-a da čuva referencu na *parent* dokument (rečenica -> paragraf).
- **T022: Query Expansion**: Korištenje LLM-a za parafraziranje korisničkog upita u 3-5 varijacija.

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
