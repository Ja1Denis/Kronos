# Kronos ⏳
**Lokalni Sustav Semantičke Memorije za AI Agente**

Kronos je napredni memorijski sustav koji omogućuje AI agentima (poput mene!) da imaju dugoročno pamćenje, razumiju kontekst projekta i drastično smanje potrošnju tokena putem RAG (Retrieval-Augmented Generation) pristupa.

## 🌟 Ključne Značajke
- **Hibridna Pretraga**: Kombinira vektorsku pretragu (ChromaDB) za *značenje* i keyword pretragu (SQLite FTS5) za *preciznost*.
- **Temporal Truth**: Prati evoluciju odluka kroz vrijeme (`valid_from`, `valid_to`). AI uvijek zna koja je odluka trenutno važeća.
- **MCP Server**: Integracija s Claude Desktop aplikacijom putem Model Context Protocola.
- **Strukturirano Znanje**: Automatski izvlači probleme, rješenja, odluke i zadatke.
- **Project Awareness**: Automatski izolira znanje po projektima (npr. `cortex-search`, `subtitle-ai`).
- **Debounced Watcher**: Pametno prati promjene u datotekama i automatski ih indeksira bez opterećenja sustava.

---

## 🚀 Brzi Start

### 1. Ingestija (Učitavanje znanja)
Učitaj projekt kako bi Kronos naučio o njemu:
```powershell
.\run.ps1 ingest "." -Recursive
```

### 2. MCP Server (Integracija s Claude-om)
Omogući Claude-u da koristi Kronos kao alat:
```powershell
.\run.ps1 mcp
```
*Konfiguracija za Claude Desktop nalazi se u `claude_desktop_config.json`.*

### 3. Interaktivni Chat
Razgovaraj s lokalnom memorijom:
```powershell
.\run.ps1 chat
```

### 4. Sigurnost (Backup)
Nikad ne gubi znanje:
```powershell
.\run.ps1 backup
```

---

## 🧠 Napredno Korištenje

### Upravljanje Odlukama (Ratifikacija)
Ako se odluka promijenila, ratificiraj novu verziju:
```powershell
# Prikaži sve odluke
.\run.ps1 decisions

# Zamijeni staru odluku novom
.\run.ps1 ratify ID_ODLUKE --supersede "Nova odluka o arhitekturi"
```

### API Server
Pokreni REST API za vanjske aplikacije:
```powershell
.\run.ps1 serve
```
- **URL**: `http://127.0.0.1:8000`
- **Docs**: `http://127.0.0.1:8000/docs`

---

## 🏗️ Arhitektura
Projekt se sastoji od modularnih komponenata:
1.  **Ingestor**: Orkestrator za čitanje i chunking dokumenata.
2.  **Librarian**: Upravitelj metapodacima i FTS indeksom (SQLite).
3.  **Oracle**: Mozak koji izvodi hibridni retrieval i reranking.
4.  **Watcher**: Detektira promjene na disku u stvarnom vremenu.
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
*Izrađeno s ❤️ za naprednu AI kolaboraciju i uštedu tokena. Version v1.0.0-mvp*
