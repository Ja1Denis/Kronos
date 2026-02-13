**DA, primijeni fix odmah**, ali uz **dodatne provjere** jer svaki od ovih problema može imati domino efekt.

***

## ✅ Problem 1: ALLOWED_ROOT - Fix Ispravan

**Što si napravio:**
```python
# Prije (prestrogo):
ALLOWED_ROOT = os.getcwd()  # /path/to/kronos

# Poslije (fleksibilnije):
if "kronos" in os.getcwd():
    ALLOWED_ROOT = os.path.dirname(os.getcwd())  # /path/to (parent)
```

**Zašto je dobro:**
- Sada može pristupiti `antigravity/`, `cortex-api/`, itd.
- Još uvijek ima security check (ne dopušta `../../../etc/passwd`)

**⚠️ Moguć problem:**
- Ako se Kronos pokrene iz **različitog direktorija** (npr. `python ../kronos/src/server.py`), `os.getcwd()` će biti nešto drugo
- **Better fix:**
  ```python
  # Use script location instead of current working directory
  SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # Where metadata_helper.py is
  KRONOS_ROOT = os.path.dirname(SCRIPT_DIR)  # /path/to/kronos
  ALLOWED_ROOT = os.path.dirname(KRONOS_ROOT)  # /path/to (project root)
  ```

**Provjera nakon fixa:**
```bash
# Test iz različitih direktorija:
cd /path/to
python kronos/src/server.py  # Radi li?

cd /path/to/kronos
python src/server.py  # Radi li?

cd /somewhere/else
python /path/to/kronos/src/server.py  # Radi li?
```

***

## ✅ Problem 2: use_hyde Bug - Jednostavan Fix

**Što se dogodilo:**
```python
# Obrisao si slučajno:
use_hyde = config.get('use_hyde', False)

# I pokušao koristiti:
if use_hyde:  # NameError!
```

**Fix:**
```python
# Vrati liniju na početak funkcije
use_hyde = config.get('use_hyde', False)
```

**⚠️ Dodaj fail-safe:**
```python
# Bolje:
use_hyde = config.get('use_hyde', False) if config else False

# Ili još bolje (defensive):
try:
    use_hyde = config.get('use_hyde', False)
except (AttributeError, KeyError):
    logger.warning("Config missing or invalid, disabling HyDE")
    use_hyde = False
```

**Provjera nakon fixa:**
```python
# Test da ne pada:
oracle.ask("test query")  # Mora raditi

# Test sa HyDE enabled:
config['use_hyde'] = True
oracle.ask("test query")  # Mora raditi

# Test sa HyDE disabled:
config['use_hyde'] = False
oracle.ask("test query")  # Mora raditi
```

***

## ⚠️ Problem 3: FTS Quote Problem - **OPREZNO!**

**Trenutni kod (pretpostavljam):**
```python
# librarian.py
def search_fts(self, query: str):
    stemmed_query = stem_query(query)
    sql = f'SELECT * FROM fts_index WHERE stemmed_content:"{stemmed_query}"'
    # Exact phrase match zbog navodnika!
```

**Problem:**
```sql
-- Query: "Što je CroStem"
-- Stemmed: "što je crostem"
-- SQL: stemmed_content:"što je crostem"

-- Nalazi SAMO ako u dokumentu piše EXACT:
"što je crostem"

-- NE nalazi ako piše:
"CroStem je projekt što..."  ❌ (riječi nisu u redoslijedu)
```

***

### Fix Opcija A: Makni Navodnike (Jednostavno ali Opasno)

```python
# Makni navodnike:
sql = f'SELECT * FROM fts_index WHERE stemmed_content:{stemmed_query}'
```

**Problem sa ovim:**
```sql
-- Query: "CroStem API"
-- Stemmed: "crostem api"
-- SQL: stemmed_content:crostem api  ❌ SYNTAX ERROR!

-- FTS5 očekuje:
stemmed_content:crostem AND stemmed_content:api
-- ili
stemmed_content:"crostem api"
```

**Također:**
```sql
-- Query: "test-feature"
-- SQL: stemmed_content:test-feature  ❌ Minus se interpretira kao operator!
```

***

### Fix Opcija B: Tokenize + AND Join (Preporučeno)

```python
def search_fts(self, query: str, top_k: int = 10):
    """
    FTS5 search with flexible matching.
    
    Converts "što je crostem" → "što AND je AND crostem"
    This finds documents containing ALL words, in ANY order.
    """
    
    # Stem query
    stemmed_query = self.stem_query(query)
    
    # Tokenize into words
    tokens = stemmed_query.split()
    
    # Escape special FTS5 characters in each token
    escaped_tokens = [self._escape_fts_token(token) for token in tokens]
    
    # Join with AND
    fts_query = ' AND '.join(escaped_tokens)
    
    logger.debug(f"FTS query: {fts_query}")
    
    # Execute
    sql = f"""
        SELECT * FROM fts_index 
        WHERE stemmed_content MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    
    results = self.db.execute(sql, (fts_query, top_k)).fetchall()
    
    return results

def _escape_fts_token(self, token: str) -> str:
    """
    Escape special FTS5 characters.
    
    FTS5 special chars: " - ( ) AND OR NOT
    """
    # Remove quotes
    token = token.replace('"', '')
    
    # Escape minus (if at start, it means NOT in FTS5)
    if token.startswith('-'):
        token = token[1:]  # Remove leading minus
    
    # Wrap in quotes if contains special chars
    special_chars = ['(', ')', '-', '+']
    if any(char in token for char in special_chars):
        token = f'"{token}"'
    
    return token
```

**Kako radi:**
```python
# Input: "što je CroStem API"
# Stemmed: "što je crostem api"
# Tokens: ["što", "je", "crostem", "api"]
# FTS Query: "što AND je AND crostem AND api"

# Nalazi:
# ✅ "CroStem je API projekt što..." (sve riječi prisutne)
# ✅ "Što je to? CroStem API!" (redoslijed nebitan)
# ❌ "CroStem projekt" (fali "što", "je", "api")
```

***

### Fix Opcija C: OR Join (Još Fleksibilnije)

```python
# Join with OR instead of AND
fts_query = ' OR '.join(escaped_tokens)

# "što OR je OR crostem OR api"

# Nalazi dokument ako sadrži BAR JEDNU riječ
# Rankira po broju matcheva
```

**Kada koristiti OR:**
- User query je general ("CroStem")
- Želiš široke rezultate (recall > precision)

**Kada koristiti AND:**
- User query je specific ("CroStem Rust stemmer")
- Želiš precizne rezultate (precision > recall)

***

### Fix Opcija D: Hybrid (Best of Both)

```python
def search_fts(self, query: str, mode: str = "and"):
    """
    mode: "and" (strict), "or" (loose), "phrase" (exact)
    """
    
    stemmed_query = self.stem_query(query)
    tokens = stemmed_query.split()
    escaped_tokens = [self._escape_fts_token(t) for t in tokens]
    
    if mode == "phrase":
        # Original behavior - exact phrase
        fts_query = f'"{stemmed_query}"'
    
    elif mode == "and":
        # All words must be present (any order)
        fts_query = ' AND '.join(escaped_tokens)
    
    elif mode == "or":
        # At least one word present
        fts_query = ' OR '.join(escaped_tokens)
    
    else:
        raise ValueError(f"Invalid mode: {mode}")
    
    # ... execute query
```

**Koristi ovako:**
```python
# Default: AND (balanced)
results = librarian.search_fts("CroStem API", mode="and")

# Strict: PHRASE (exact match)
results = librarian.search_fts("release v0.2.62", mode="phrase")

# Loose: OR (broad search)
results = librarian.search_fts("config database setup", mode="or")
```

***

## 🎯 Moja Preporuka: **Opcija D (Hybrid)**

**Razlozi:**
1. **Backward compatible** - možeš držat "phrase" mode za specifične upite
2. **Flexible** - default "and" će raditi za 80% slučajeva
3. **Debuggable** - lako testiraš različite modes
4. **Future-proof** - možeš dodati "fuzzy", "wildcard" modove kasnije

***

## 📋 Implementacijski Plan:

### **Step 1: Update librarian.py (10 min)**
```python
# Add hybrid search function (Opcija D)
# Test locally: python -c "from librarian import Librarian; l = Librarian(); print(l.search_fts('test'))"
```

### **Step 2: Update oracle.py (5 min)**
```python
# Change how Oracle calls Librarian:
results = self.librarian.search_fts(query, mode="and")  # Default AND
```

### **Step 3: Test Suite (15 min)**
```python
# Test cases:
test_queries = [
    ("CroStem", "and"),  # Should find any doc mentioning CroStem
    ("što je CroStem", "and"),  # All words present, any order
    ("release v0.2.62", "phrase"),  # Exact phrase
    ("config setup database", "or"),  # At least one word
]

for query, mode in test_queries:
    results = librarian.search_fts(query, mode=mode)
    print(f"{query} ({mode}): {len(results)} results")
    if results:
        print(f"  Top: {results[0]['content'][:100]}")
```

### **Step 4: Re-index (ako treba) (5 min)**
```bash
# Ako si mijenjao stemming logic, trebat će re-index
python scripts/ingest_all.py
```

### **Step 5: Integration Test (10 min)**
```bash
# Pokreni Kronos
python src/server.py

# Test query kroz API
curl -X POST http://localhost:8000/query -d '{"text": "što je CroStem"}'

# Provjeri: Dobivaju li se rezultati?
```

***

## ⚠️ Što Provjeriti Nakon Svih Fixeva:

### **1. Security Check**
```bash
# Pokušaj path traversal
curl -X POST http://localhost:8000/fetch_exact \
  -d '{"file_path": "../../../etc/passwd", "start_line": 0, "end_line": 10}'

# Expected: Error (blocked by is_safe_path)
```

### **2. FTS Performance**
```python
# Measure query time
import time

start = time.time()
results = librarian.search_fts("test query", mode="and")
elapsed = time.time() - start

print(f"Query took {elapsed*1000:.2f}ms")  # Should be <50ms
```

### **3. Result Quality**
```python
# Manual spot check
query = "što je CroStem"
results = librarian.search_fts(query, mode="and")

for r in results[:5]:
    print(f"Score: {r['score']}, File: {r['source']}")
    print(f"Content: {r['content'][:200]}...")
    print("---")

# Pitaj sebe: Jesu li ovi rezultati relevantni?
```

### **4. Edge Cases**
```python
# Test problematic queries:
edge_cases = [
    "",  # Empty
    "a",  # Single char
    "što je-to",  # Hyphen
    "config (production)",  # Parentheses
    '"quoted text"',  # Already has quotes
    "test AND debug",  # Contains FTS operator
]

for query in edge_cases:
    try:
        results = librarian.search_fts(query, mode="and")
        print(f"✅ '{query}': {len(results)} results")
    except Exception as e:
        print(f"❌ '{query}': {e}")
```

***

## 🚨 Rizici Koje Trebaš Znati:

### **Rizik 1: Precision Pad**
- AND mode će vratit **manje rezultata** nego phrase mode
- Ako query ima puno riječi ("što je to CroStem Rust stemming library"), može vratit **0 rezultata** jer svi dokumenti nemaju SVE riječi

**Mitigation:** Fallback na OR ako AND vrati 0:
```python
results = librarian.search_fts(query, mode="and")
if len(results) == 0:
    logger.info("AND returned 0, trying OR fallback")
    results = librarian.search_fts(query, mode="or")
```

### **Rizik 2: Stopwords Problem**
- Ako query je "što je to", a svi dokumenti imaju "što", "je", "to", sve će biti relevant (lažno pozitivno)

**Mitigation:** Filter stopwords prije FTS:
```python
STOPWORDS = {'je', 'to', 'i', 'u', 'na', 'za', 'od', 'do'}

def preprocess_query(query):
    tokens = query.lower().split()
    filtered = [t for t in tokens if t not in STOPWORDS]
    return ' '.join(filtered) if filtered else query  # Don't return empty
```

### **Rizik 3: AND vs OR User Expectation**
- User možda očekuje phrase match, dobije AND match
- Rezultati su "relevantni" ali ne "exact"

**Mitigation:** Dodaj u response metadata:
```python
{
    "results": [...],
    "search_mode": "and",
    "message": "Found documents containing ALL query words (in any order)"
}
```

***

## ✅ Final Checklist Prije Production:

- [ ] `is_safe_path` testiran sa različitim `cwd`
- [ ] `use_hyde` bug fixan + defensive check dodan
- [ ] FTS query hybrid mode implementiran
- [ ] `_escape_fts_token` handla sve special chars
- [ ] Fallback AND → OR ako 0 results
- [ ] Stopwords filtered (opciono)
- [ ] Edge case queries testirane
- [ ] Performance benchmark (<50ms per query)
- [ ] Security test (path traversal blocked)
- [ ] Integration test kroz API (curl)
- [ ] Log review (nema error-a u zadnjih 10 querya)

***

**TL;DR:** 
1. ✅ Fix 1 (ALLOWED_ROOT) je OK, ali provjeri sa `__file__` umjesto `getcwd()`
2. ✅ Fix 2 (use_hyde) je trivijalan, dodaj defensive check
3. ⚠️ Fix 3 (FTS quotes) → **Koristi Opciju D (Hybrid)**, testiraj opsesivno

