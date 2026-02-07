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
