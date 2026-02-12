# Kronos ⏳
**Lokalni Sustav Semantičke Memorije za AI Agente**

Kronos je napredni memorijski sustav koji omogućuje AI agentima (poput mene!) da imaju dugoročno pamćenje, razumiju kontekst projekta i drastično smanje potrošnju tokena putem RAG (Retrieval-Augmented Generation) pristupa.

## 🌟 Ključne Značajke
- **Rust Fast-Path (L0/L1)**: Ultra-brza pretraga poznatih pojmova implementirana u **Rustu** (**< 1ms**). Preskače tešku artiljeriju (LLM/Vector) za instantne odgovore.
- **Hibridna Pretraga**: Kombinira vektorsku pretragu (ChromaDB) za *značenje* i keyword pretragu (SQLite FTS5) za *preciznost*.

- **Temporal Truth**: Prati evoluciju odluka kroz vrijeme (`valid_from`, `valid_to`). AI uvijek zna koja je odluka trenutno važeća.
- **MCP Server**: Integracija s Claude Desktop aplikacijom putem Model Context Protocola.
- **Strukturirano Znanje**: Automatski izvlači probleme, rješenja, odluke i zadatke.
- **Project Awareness**: Automatski izolira znanje po projektima (npr. `cortex-search`, `subtitle-ai`).
- **Debounced Watcher**: Pametno prati promjene u datotekama i automatski ih indeksira bez opterećenja sustava.

---

## 🚀 Brzi Start

### 1. Ultra-Brza Pretraga (Desktop) 🚀
Za trenutne odgovore bez čekanja:
1.  **Dvaput klikni** na ikonu **"Kronos Server"** na radnoj površini.
2.  Kada dobiješ potvrdu da je spreman, koristi:
```powershell
.\ask_fast.ps1 -Query "tvoje pitanje"
```

### 2. One-Click Chat 🖱️
Sada možeš pokrenuti interaktivni chat direktno s Desktopa koristeći ikonu **"Kronos AI Chat"** ili:
```powershell
.\run_chat.bat
```

### 2. Ingestija (Učitavanje znanja)
Učitaj projekt kako bi Kronos naučio o njemu:
```powershell
.\run.ps1 ingest "." -Recursive
```

### 3. Ručni Unos Znanja
Dodaj važnu informaciju ili odluku bez pisanja datoteka:
```powershell
python -m src.cli save "Opis tvoje odluke" --as decision --project kronos
```

---

## 🧠 Napredno Korištenje

### Upravljanje Odlukama i Povijest
Kronos prati evoluciju tvog razmišljanja:
```powershell
# Zamijeni staru odluku novom
.\run.ps1 ratify ID --supersede "Nova verzija odluke"

# Pogledaj timeline promjena
.\run.ps1 history ID
```

### Multi-Project Dashboard
Vidi stanje svih svojih projekata:
```powershell
.\run.ps1 projects
```

### Benchmark & Rebuild
Provjeri performanse ili rekonstruiraj bazu iz arhive:
```powershell
.\run.ps1 benchmark   # Test pretrage i latencije
.\run.ps1 rebuild     # Potpuna rekonstrukcija iz archive.jsonl
```

---

## 🏗️ Arhitektura (Kronos 2.0)
Projekt se sastoji od modularnih komponenata:
1.  **Ingestor**: Orkestrator za čitanje dokumenata.
2.  **Librarian**: Upravitelj metapodacima i FTS indeksom. Podržava **Event Sourcing**.
3.  **Oracle**: 3-stage hybrid retrieval pipeline (Keyword -> Vector -> Reranking).
4.  **Watcher**: Real-time indeksiranje promjena.
5.  **MCP Server**: Bridge prema modernim AI klijentima.

---

## 📊 Zašto Kronos? (Token Ekonomija)
Ušteda na tokenima pri radu s velikim projektima iznosi preko **95%**.
- **Bez Kronosa**: 5000+ tokena konteksta po upitu.
- **S Kronosom**: ~200 tokena preciznog konteksta.

---

## 🛠️ Razvoj i Testiranje
Pokreni kompletan testni paket:
```powershell
.\venv\Scripts\pytest tests/ -v
```

---
*Izrađeno s ❤️ za naprednu AI kolaboraciju. Version v2.1.0-beta-rust*
