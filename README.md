# Kronos ⏳
**Lokalni Sustav Semantičke Memorije za AI Agente**

Kronos je napredni memorijski sustav koji omogućuje AI agentima (poput mene!) da imaju dugoročno pamćenje, razumiju kontekst projekta i brzo pronalaze informacije.

## 🌟 Ključne Značajke
- **Hibridna Pretraga**: Kombinira vektorsku pretragu (ChromaDB + Sentence Transformers) za *značenje* i keyword pretragu (SQLite FTS5 + CroStem) za *preciznost*.
- **Strukturirano Znanje**: Automatski izvlači probleme, rješenja, odluke i zadatke iz teksta.
- **Daemon Mode (Watcher)**: Prati tvoje promjene u datotekama u stvarnom vremenu i automatski ih pamti.
- **Developer-First**: Dizajniran da se koristi kroz CLI (za ljude) i API (za agente).

---

## 🚀 Brzi Start

### 1. Ingestija (Učitavanje znanja)
Učitaj sve dokumente iz trenutnog direktorija kako bi Kronos naučio o projektu.
Kronos automatski prepoznaje ime projekta iz mape!

```powershell
# Učitaj projekt (npr. iz foldera 'moj-projekt')
.\run.ps1 ingest "." -Recursive
```

### 2. Interaktivni Chat (NOVO!)
Razgovaraj s Kronosom o svojim projektima u prirodnom jeziku:
```powershell
.\run.ps1 chat
```
*Kronos pametno filtrira odgovore ovisno o projektu kojeg spomeneš u pitanju!*

### 3. Eksplicitna Pretraga (CLI)
Pitaj Kronosa bilo što o specifičnom projektu:
```powershell
.\run.ps1 ask "Kako radi Watcher modul?" --project kronos
```

### 4. Statistika
Provjeri stanje memorije:
```powershell
.\run.ps1 stats
```

---

## 🧠 Napredno Korištenje

### API Server (Za AI Agente)
Pokreni server koji omogućuje agentima da programski pristupaju memoriji:
```powershell
.\run.ps1 serve
```
- **URL**: `http://127.0.0.1:8000`
- **Dokumentacija**: `http://127.0.0.1:8000/docs`
- **Automatski Watcher**: Server automatski prati `docs/` folder i re-indeksira promjene.

### Daemon Mode (Samo Watcher)
Ako ne trebaš server, već samo želiš da Kronos prati promjene u pozadini:
```powershell
.\run.ps1 watch "."
```

---

## 🏗️ Arhitektura
Projekt se sastoji od 4 glavna modula:
1.  **Ingestor**: Čitač datoteka, chunker i orkestrator.
2.  **Librarian**: Upravitelj SQLite bazom (metapodaci, FTS indeks, entiteti).
3.  **Oracle**: Mozak operacije - izvodi hibridnu pretragu i rangira rezultate.
4.  **Watcher**: Oči sustava - detektira promjene na disku.

Podaci se čuvaju u:
- `data/store`: ChromaDB (vektori)
- `data/metadata.db`: SQLite (FTS5 + Entiteti)
- `data/archive.jsonl`: Sirovi JSON log (backup)

## 🛠️ Razvoj
Testiranje sustava:
```powershell
.\venv\Scripts\pytest
```

---
*Izrađeno s ❤️ za naprednu AI kolaboraciju.*
