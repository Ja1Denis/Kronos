# Tim Specijaliziranih Agenata (Modula)

Da bi projekt Kronos uspješno funkcionirao, ne koristimo jednog "monolitnog" agenta, već tim visoko specijaliziranih modula. Svaki agent ima jasnu odgovornost i input/output specifikaciju.

## 1. Agent Ingestor (🕳️ "Gutač")
**Uloga:** Prva linija obrane. Njegov posao je pročitati svaku datoteku, log i razgovor.
-   **Zadaci:**
    -   Skenira direktorije (`src`, `docs`).
    -   Čisti tekst (uklanja boilerplate, prazne linije).
    -   Vrši **"Chunking"** (dijeli tekst na manje, logične cjeline).
    -   Primjenjuje **CroStem** za hrvatski jezik (stemming).

## 2. Agent Extractor (🧪 "Analitičar")
**Uloga:** Srce "Kronoraising" arhitekture. Pretvara nestrukturirani tekst u strukturirano znanje.
-   **Zadaci:**
    -   Prepoznaje entitete (Tko, Što, Gdje).
    -   Izvlači **Odluke** ("Odlučili smo X").
    -   Prepoznaje **Probleme** i povezuje ih s **Rješenjima**.
    -   Izdvaja **Kodne Promjene** (diffove).
-   **Alati:** Regex, NLP, mini AI modeli.

## 3. Agent Librarian (📚 "Knjižničar")
**Uloga:** Čuvar baze podataka. Pazi na efikasnost pohrane.
-   **Zadaci:**
    -   Upravlja s **ChromaDB** (vektorska baza).
    -   Upravlja s **SQLite** (metapodaci).
    -   Indeksira sadržaj (Full-Text Search).
    -   Komprimira stare razgovore (JSONL).

## 4. Agent Oracle (🔮 "Proročište")
**Uloga:** Sučelje prema korisniku/glavnom AI agentu.
-   **Zadaci:**
    -   Prima upit ("Kako riješiti X?").
    -   Vrši **Hybrid Search** (BM25 + Vektori).
    -   Rerankira rezultate (bira najbolje).
    -   Vraća **samo relevantni kontekst**.

## 5. Agent Orchestrator (🎼 "Dirigent")
**Uloga:** Glavni proces koji koordinira sve ostale.
-   **Zadaci:**
    -   Triggerira Ingestora (npr. na `git commit`).
    -   Upravlja pipelineom podataka.
    -   Logira pogreške i metriku uspješnosti.

---

## 🆕 Novi Članovi Tima (Faza 4)

## 6. Agent Archivist (📜 "Arhivar")
**Uloga:** Čuvar Event Loga i garant integriteta podataka.
-   **Zadaci:**
    -   Upravlja `archive.jsonl` kao primarnim izvorom istine.
    -   Implementira event schema (insert/update/delete).
    -   Pokreće **rebuild** procedure za regeneraciju baza iz loga.
    -   Validira konzistentnost između JSONL ↔ SQLite ↔ ChromaDB.
-   **Alati:** JSON streaming, checksum validacija, migration skripte.

## 7. Agent Evaluator (📊 "Sudac")
**Uloga:** Mjeri i dokazuje kvalitetu Kronosa.
-   **Zadaci:**
    -   Pokreće **benchmark suite** nad test pitanjima.
    -   Mjeri Recall@K, Context Tokens, Latency.
    -   Generira izvještaje (Markdown/PDF).
    -   Uspoređuje različite retrieval strategije (A/B testiranje).
-   **Alati:** pytest, statistika, vizualizacija.

## 8. Agent Promoter (⭐ "Kurator")
**Uloga:** Pretvara sirove podatke u strukturirano znanje.
-   **Zadaci:**
    -   Omogućuje `save` komandu za brzi unos činjenica/odluka.
    -   Implementira `promote` za pretvaranje search rezultata u trajne zapise.
    -   Detektira duplikate i konflikte.
    -   Predlaže tipizaciju (Decision/Fact/Task) na temelju sadržaja.
-   **Alati:** NLP klasifikacija, duplicate detection, user interaction.

## 9. Agent Historian (⏳ "Povjesničar")
**Uloga:** Prati evoluciju znanja kroz vrijeme.
-   **Zadaci:**
    -   Vraća **povijest promjena** za odluke i činjenice.
    -   Detektira **kontradikcije** između starih i novih zapisa.
    -   Generira **timeline** prikaz evolucije projekta.
    -   Odgovara na pitanja tipa "Kako se X mijenjao?"
-   **Alati:** Temporal queries, diff algoritmi, vizualizacija vremenske crte.
