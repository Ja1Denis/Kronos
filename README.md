# Kronos ⏳
**Lokalni Sustav Semantičke Memorije za AI Agente**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: Beta-Rust](https://img.shields.io/badge/Status-Beta--Rust-orange.svg)]()

Kronos je napredni memorijski sustav koji omogućuje AI agentima dugoročno pamćenje i duboko razumijevanje konteksta projekta uz **drastično smanjenje troškova** putem inovativnog "Pointer-based" RAG pristupa.

---

## 💰 Efikasnost Tokena - Kronos Prednost

### Zašto su "Pointeri" (pokazivači) važni?

Tradicionalni RAG sustavi šalju **cijele blokove dokumenata** vašem LLM-u, trošeći ogromne količine tokena. Kronos umjesto toga šalje **lagane pokazivače**, dopuštajući AI-u da sam odluči što mu zaista treba.

### Vizualna usporedba

```text
┌─────────────────────────────────────────────────────────────┐
│ Tradicionalni RAG (Šalje sav sadržaj)                       │
│ ████████████████████████████████████████████  15,000 tokena │
│ Trošak: $0.021 po upitu                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Kronos Pointeri (Samo metapodaci)                           │
│ ██ 300 tokena                                               │
│ Trošak: $0.00042 po upitu                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Kronos Smart Fetch (Pointeri + Selektivni sadržaj)          │
│ ████████ 2,500 tokena                                       │
│ Trošak: $0.0035 po upitu                                    │
└─────────────────────────────────────────────────────────────┘

📉 **83-98% smanjenje broja tokena**
💵 **5-50x ušteda na troškovima**
```

### Stvarni izračun troškova

Bazirano na **Gemini 1.5 Flash-8B** cijenama ($0.14/1M tokena):

| Mjesečni volumen  | Tradicionalni RAG | Kronos (Samo Pointeri) | Kronos (Smart Fetch) | Godišnja ušteda |
|-------------------|-------------------|------------------------|----------------------|-----------------|
| **1,000 upita**   | $21               | $0.42                  | $3.50                | **$210-246**    |
| **10,000 upita**  | $210              | $4.20                  | $35                  | **$2,100-2,460**|
| **100,000 upita** | $2,100            | $42                    | $350                 | **$21,000-24,600**|

<sub>*Izračunato s 15k tokena/upit (RAG), 300 tokena/upit (Pointer), 2.5k tokena/upit (Smart Fetch)*</sub>

💡 **Break-even točka: ~500 upita** (Kronos se isplaćuje u danima, ne mjesecima!)

---

## 🌟 Ključne Značajke

- ⚡ **Rust Fast-Path (L0/L1)**: Ultra-brza pretraga pojmova implementirana u Rustu (**< 1ms**).
- 🔍 **Hibridna Pretraga**: Kombinacija vektorske pretrage (ChromaDB) i precizne FTS5 pretrage (SQLite).
- ⚖️ **Temporal Truth**: Prati evoluciju odluka kroz vrijeme (`valid_from`, `valid_to`).
- 📂 **Project Awareness**: Automatska izolacija znanja po projektima.
- 🛠️ **Smart Fetching**: AI samostalno zahtijeva točne linije koda tek kada su mu potrebne.

---

## 🏗️ Arhitektura (High-Level)

```text
[ AI Client / Antigravity ] <--> [ FastAPI Server (Port 8000) ]
                                          |
        ┌─────────────────────────────────┴──────────────────────────────┐
        ▼                                 ▼                              ▼
 [ Rust FastPath ]                [ SQLite (FTS5) ]              [ ChromaDB (Vector) ]
 (Literal Matches)                (Keyword Rank)                 (Semantic Score)
        │                                 │                              │
        └─────────────────────────────────┬──────────────────────────────┘
                                          ▼
                         [ Oracle (Reranking & Selection) ]
                                          │
                                 [ Context Budgeter ]
```

---

## 🚀 Brzi Start

### 1. Instalacija
```powershell
# Kloniraj repozitorij i instaliraj ovisnosti
git clone https://github.com/Ja1Denis/Kronos.git
cd Kronos
pip install -r requirements.txt
```

### 2. Pokreni Ingestiju (Učitavanje znanja)
```powershell
# Učitaj cijeli radni prostor odjednom
python .\ingest_everything.py
```

### 3. Pokreni Server
```powershell
# Postavi PYTHONPATH i pokreni API
$env:PYTHONPATH="."; python src/server.py
```

### 4. Prvi Upit
```powershell
.\ask_fast.ps1 -Query "Što Kronos radi sa tokenima?"
```

---

## 🛠️ Razvoj i Maintenance

### Reset i Čišćenje
Ako želiš svjež početak:
```powershell
# Prisilni wipe bez potvrde
.\run.ps1 wipe --force
```

### Testiranje
```powershell
python -m pytest tests/ -v
```

---

## 📝 Licenca i Zasluge
Izrađeno s ❤️ za naprednu AI kolaboraciju.
Licencirano pod **MIT Licencom**.
