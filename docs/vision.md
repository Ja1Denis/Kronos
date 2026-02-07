# Kronos: Semantički Operativni Sustav za AI Memoriju

## 🎯 Cilj
Stvoriti sustav koji drastično smanjuje potrošnju tokena (do 97%) i povećava inteligenciju AI agenta kroz strukturiranu, semantičku memoriju.

## 🧠 Koncept: "Tri Razine Rješenja"

### 1. Laka Razina (Quick Win)
- **Metoda:** Klasični sažetak (5-10 rečenica po razgovoru).
- **Storage:** SQLite FTS5 (Full-Text Search).
- **Workflow:** Agent traži ključne riječi -> Dobiva sažetak.
- **Ušteda:** ~70-85%.

### 2. Srednja Razina (Sweet Spot - MVP)
- **Metoda:** Hibridno pretraživanje (Keyword + Semantic).
- **Filtriranje 1:** BM25 / CroStem (odbacuje 90% šuma).
- **Filtriranje 2:** Mini Embedding Model (lokalni `all-MiniLM-L6-v2`).
- **Reranking:** Top 3-5 kandidata se šalje agentu.
- **Dohvat:** Relevantni *dijelovi* razgovora.
- **Ušteda:** ~92-97%.

### 3. Hardcore Razina ("Kronoraising" Arhitektura) 🏆
Ovo je konačni cilj. Pretvaranje teksta u strukturirano znanje.

#### Pipeline:
`Razgovor → Extraction Pipeline → Hierarchical Storage`

**Extraction Pipeline:**
1.  **Entities:** Tko, što, gdje.
2.  **Decisions:** "Odlučili smo X".
3.  **Code Changes:** Diffovi, funkcije (ne puni kod).
4.  **Problems & Solutions:** Povezani parovi (Problem: "Timeout", Rješenje: "Workers").
5.  **References:** Poveznice na druge razgovore.

**Hierarchical Storage:**
1.  **Hot Cache (Redis):** Zadnjih 2h razgovora.
2.  **Warm Index (SQLite):** Aktivni tjedan.
3.  **Cold Archive (Compressed JSONL):** Sve ostalo.

## 💡 Primjer Uštede

**Upit:** "Kako sam implementirao CroStem plugin?"

| Metoda | Tokeni | Cijena | Vrijeme |
| :--- | :--- | :--- | :--- |
| **Bez Optimizacije** | 120,000 | $0.60 | 8s |
| **Kronos (Optimizirano)** | 800 | $0.004 | 1.2s |
| **Povećanje Efikasnosti** | **150x** | **99%** | **Fast** |
