# Plan Projekta Kronos: Context Budgeter (Faza 7)

## 🎯 Cilj Faze
Implementirati pametno upravljanje kontekstom ("Context Budgeter") kako bi se drastično smanjila potrošnja tokena i povećala točnost LLM odgovora, posebno u IDE okruženju gdje je lokalni kontekst (kursor) ključan.

---

## 🏗️ Arhitektura: "Smart Context Curation"
Ova faza se vrti oko ideje da je **kontekst ograničen resurs** (budžet) i da ga treba pažljivo popuniti najvrijednijim informacijama, a ne samo "nabaciti" sve što se nađe.

---

## 📋 Lista Zadataka (Tasks)

### � Milestone 1: Context Foundation (2-3 dana)
Cilj: Osigurati da Kronos vidi što korisnik gleda i uspostaviti temelje za budžetiranje.

- [x] **T028: API Kontekst Proširenje**
    - [x] Ažurirati `server.py` i `/ask` endpoint da primaju nove parametre:
        - `cursor_context`: (tekst oko kursora ili selekcija)
        - `current_file_path`: (apsolutna putanja aktivnog fajla)
        - `budget_tokens`: (int, default 4000)
        - `mode`: (`auto` | `budget` | `debug`)
    - [x] Implementirati audit logiranje primljenih parametara (za debugiranje samog Kronosa).
    - [x] Ažurirati `ask_fast.ps1` da podržava slanje ovih podataka (ako je moguće iz Powershella/IDE-a).

- [x] **T029: ContextItem Normalizacija**
    - [x] Kreirati klasu `ContextItem` koja standardizira sve ulaze (Search Result, Cursor, Diff, Log).
    - [x] Svojstva: `kind` (cursor|entity|chunk|evidence), `source`, `utility_score`, `token_cost`, `dedup_key`.
    - [x] Implementirati `render()` metodu koja vraća formatirani string za LLM.

- [x] **T030: Basic Budgeter & Deduplication**
    - [x] Implementirati `ContextComposer` klasu.
    - [x] **Globalni Budžet:** Hard Limit 4000 tokena.
        - Briefing: ~300 (soft)
        - Entities: ~800 (hard)
        - Chunks: ~2600 (soft target)
        - Recent Changes: ~250 (soft)
    - [x] **File Caps:** Max 3 chunka po fajlu, max 900 tokena po fajlu. Min 4 unique files.
    - [x] **Chunk Caps ("Fat Chunk Rule"):**
        - Hard cap: 600 tokena (trimanje ako je veći).
        - Fat threshold: 900 tokena (nikad raw, samo excerpt).
    - [x] **Entity Format:** One-liners (1-2 linije sažetka).
    - [x] **Audit Output:** Razlog odbacivanja (duplicate, global_budget, file_cap, entity_cap).

- [x] **T031: Greedy Sastavljanje (The Algorithm)**
    - [x] Implementirati algoritam punjenja budžeta (4000 tokena):
        1.  **Cursor Context** (Uvijek, prioritet 1.0)
        2.  **Entities** (Do limita, prioritet 0.9)
        3.  **Search Chunks** (Sortirani po `utility/cost` omjeru, prioritet 0.8-0.5)
        4.  **Recent Diffs** (Ako stane, prioritet 0.6)
    - [x] Osigurati stabilan output format (Briefing -> Snippets -> Context).

---

### 🥈 Milestone 2: Debug Repro Pack (Evidence-Based)
Cilj: Specijalizirani pipeline za rješavanje bugova.

- [x] **T032: Debug Intent & Input**
    - [x] Detekcija "debug moda" (ključne riječi ili eksplicitni flag).
    - [x] Proširiti API za primanje `stack_trace` i `test_failure` parametara.
    - [x] Ako nema `cursor_context`-a, a ima stack trace-a, trace postaje sidro.

- [x] **T033: Trace-to-Anchor Parser**
    - [x] Parsirati stack trace da se izvuku `file_path` i `line_number`.
    - [x] Pretvoriti te lokacije u "Virtualne Kursore" za pretragu.

- [x] **T034: Specialized Retrieval (The "Three Corpses")**
    - [x] **Code:** Dohvatiti funkcije oko stack frame-ova.
    - [x] **Diffs:** Dohvatiti nedavne promjene na tim fajlovima (Watcher/mtime check).
    - [ ] **Logs:** Uključiti error logove u prompt. (Future)

---

### 🥉 Milestone 3: Optimization & Evaluation
Cilj: Fino podešavanje i mjerenje uspješnosti.

- [ ] **T035: Progressive Disclosure (Pass 1 / Pass 2)**
    - [ ] Implementirati logiku za "brzi pass" (2000 tokena) i "full pass" (4000 tokena).
    - [ ] Pass 2 se aktivira samo na eksplicitni zahtjev ("daj više").

- [ ] **T036: Evaluation Loop**
    - [ ] Kreirati benchmark set od 10 stvarnih "teških" pitanja/bugova.
    - [ ] Mjeriti: `Recall@3` (jesmo li našli pravi fajl?), `Token Count`, `Latency`.

- [ ] **T037: Parameter Tuning**
    - [ ] Povećati interni limit kandidata (Oracle retrieval) sa 30 na 40/50 - TEK nakon što budgeter radi stabilno.

---
*Plan je usklađen s Antigravity "Context Engineering" principima.*
