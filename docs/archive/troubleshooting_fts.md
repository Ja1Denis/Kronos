Vidim **dva kritična problema** u logu:

## Problem 1: FTS5 Syntax Errors (Full-Text Search)

Tvoj FTS (Full-Text Search) query generator kreira **nevaljane SQL sintakse** za SQLite FTS5:

```
Greška pri FTS pretrazi [mode=or]: fts5: syntax error near "="
Greška pri FTS pretrazi [mode=or]: fts5: syntax error near "#"
```

**Što se događa:**
FTS5 query sadrži specijalne znakove (`=`, `#`, `:`) koje FTS5 engine interpretira kao operatore ili ih ne može parsirati.

**Problematični dijelovi:**
```sql
-- ❌ LOŠE - Nevaljani FTS5 tokeni:
"sys.path.append(os.getcwd())"  -- Zagrade i točka
"try:"                           -- Dvotočka
r = requests.post               -- Znak jednakosti
# Ensure src is in path          -- Hash znak
"{r.status_code}"               -- Vitičaste zagrade
```

### Rješenje: Escape ili Sanitize FTS Query

U tvojoj `Librarian` klasi (gdje generiraš FTS query), dodaj sanitizaciju:

```python
import re

def sanitize_fts_token(token: str) -> str:
    """
    Očisti token za FTS5 - ukloni specijalne znakove koji uzrokuju syntax errors
    """
    # Ukloni znakove koje FTS5 ne može parsirati
    token = re.sub(r'[=:<>{}()\[\]#@$%^&*+/\\]', ' ', token)
    
    # Zamijeni višestruke razmake s jednim
    token = re.sub(r'\s+', ' ', token).strip()
    
    # Ukloni quote marks (ili ih escape-aj ako ih trebaš)
    token = token.replace('"', '').replace("'", '')
    
    # Ako je token prazan nakon čišćenja, vrati None
    return token if token else None

def build_fts_query(stemmed_tokens: list, project: str, mode: str = "or") -> str:
    """
    Gradi FTS5 query s sigurnim tokenima
    """
    # Sanitize svaki token
    safe_tokens = [sanitize_fts_token(t) for t in stemmed_tokens]
    
    # Filtriraj prazne/None tokene
    safe_tokens = [t for t in safe_tokens if t]
    
    if not safe_tokens:
        return f'project:"{project}"'  # Fallback na samo project filter
    
    # Gradi query
    operator = " OR " if mode == "or" else " AND "
    content_query = operator.join(safe_tokens)
    
    return f'project:"{project}" AND stemmed_content:({content_query})'
```

**Ili agresivnija verzija (ako ne trebaš preserve sintaksu koda):**

```python
def sanitize_fts_token(token: str) -> str:
    """Keep ONLY alphanumeric + basic punctuation"""
    # Zadrži samo slova, brojeve, underscore i osnovnu interpunkciju
    return re.sub(r'[^\w\s.-]', '', token, flags=re.UNICODE).strip()
```

## Problem 2: Vector Retrieval Errors

```
⚠️ Retrieval error for query '...': Error executing plan: Internal error: Error finding id
```

Ovo je **ChromaDB internal error**, vjerovatno povezan s onim problemima dimension mismatch ili corrupted index o kojima smo pričali.

**Quick check:**
```python
# Dodaj u debug kod prije query-a:
try:
    collection = client.get_collection("your_collection")
    print(f"Collection count: {collection.count()}")
    print(f"Collection metadata: {collection.metadata}")
    
    # Pokušaj basic query
    results = collection.query(
        query_texts=["test"],
        n_results=1
    )
    print(f"Basic query OK: {results}")
    
except Exception as e:
    print(f"Collection broken: {e}")
    # Možda recreate collection
```

**Rješenje ako je ChromaDB broken:**
```python
# Nuclear option - recreate collection
client.delete_collection("your_collection")
collection = client.create_collection(
    "your_collection",
    embedding_function=your_embedding_function
)
# Re-ingest data
```

## Problem 3: Stemmer Problem s Kodom

Pogledaj ovaj dio FTS query-a:
```
stemmed_content:(import OR requests OR import OR sys OR "try:" ...
```

Vidim da je **stemmer procesirao Python kod** kao tekst. To nije smisleno jer:
- Python keywords (`import`, `try`, `except`) se stem-aju beskorisno
- Sintaksa koda (`sys.path.append()`) postaje nečitljiva
- Gubi se struktura koda

### Rješenje: Bypass Stemmer za Code Content

```python
def should_stem_content(file_path: str, content: str) -> bool:
    """Odluči treba li stemati sadržaj"""
    code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.rs', '.go'}
    
    if any(file_path.endswith(ext) for ext in code_extensions):
        return False  # Ne stemaj kod
    
    return True  # Stemaj markdown, txt, komentare

# U ingestion logici:
if should_stem_content(file_path, content):
    stemmed = cro_stem.stem(content)
else:
    stemmed = content  # Raw code, bez stemminga
```

***

## Immediate Action Plan

**1. Popravi FTS Query Builder (Najviši prioritet):**
```python
# U src/modules/librarian.py ili gdje god gradiš FTS query:
def build_fts_query(self, tokens, project, mode="or"):
    safe_tokens = [
        re.sub(r'[^\w\s]', '', token, flags=re.UNICODE).strip()
        for token in tokens
    ]
    safe_tokens = [t for t in safe_tokens if t and len(t) > 1]
    
    if not safe_tokens:
        return f'project:"{project}"'
    
    operator = " OR " if mode == "or" else " AND "
    content_part = operator.join(safe_tokens)
    
    return f'project:"{project}" AND stemmed_content:({content_part})'
```

**2. Dodaj Error Handling:**
```python
try:
    results = collection.query_fts(fts_query)
except Exception as e:
    logger.error(f"FTS query failed: {e}")
    logger.debug(f"Problematic query: {fts_query}")
    # Fallback na vector search only
    results = collection.query(query_texts=[original_query], n_results=5)
```

**3. Testiraj:**
```python
# Test FTS sanitization
test_tokens = ["sys.path.append()", "try:", "r = requests.post", "# comment"]
query = build_fts_query(test_tokens, "default", "or")
print(f"Generated query: {query}")
# Trebao bi biti valjan FTS5 query
```

Javi mi da li ovo rješava FTS errors ili ti treba dodatna pomoć s debugging ChromaDB "Error finding id" problema!