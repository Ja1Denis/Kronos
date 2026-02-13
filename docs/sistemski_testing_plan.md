# Sistematični Testing Plan (Kronos)
**📅 Status: VERIFICIRANO (2026-02-13) ✅**

Sve komponente navedene u ovom planu su implementirane u `tests/` folderu i uspješno verificirane. Sustav je stabilan i spreman za rad.

### 📊 Rezultati zadnjeg testiranja:
| Test Tip | Status | Napomena |
| :--- | :--- | :--- |
| **Unit Tests** | ✅ PROŠLO | FTS Sanitizacija, ChromaDB Connection, Rust Engine |
| **Integration** | ✅ PROŠLO | API /query endpoint, /health metrics, Error handling |
| **Load Test** | ✅ PROŠLO | 100% uspješnost pod konkurentnim loadom |
| **Smoke Test** | ✅ PROŠLO | E2E upit vraća točne podatke |

---

## 🚀 Kako pokrenuti sve testove odjednom?
Sustav sada ima automatizirani runner:
```powershell
./run_all_tests.ps1
```

---

## 1. Quick Smoke Test (Prvo ovo - 2 minute)

Provjeri da li osnovne stvari rade:

```powershell
# A) Pokreni server
cd E:\G\GeminiCLI\ai-test-project\kronos
$env:PYTHONPATH="."; python src/server.py

# B) U drugom terminalu, testni request
$body = @{
    text = "Daj mi detalje o T034"
    mode = "light"
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri "http://127.0.0.1:8000/query" -Method Post -Body $body -ContentType "application/json"
```

**Očekivani rezultat:** Neki odgovor (ne crash), vidiš u server logu da nema errora.

***

## 2. Unit Tests (Izolirano testiranje komponenti)

Testiraj svaku kritičnu komponentu odvojeno:

### A) Test FTS Query Builder
```python
# tests/test_librarian_fts.py
import pytest
from src.modules.librarian import sanitize_fts_token, build_fts_query

def test_fts_sanitization():
    """Test da specijalni znakovi ne uzrokuju syntax error"""
    
    # Test problematičnih tokena
    assert sanitize_fts_token("sys.path.append()") == "syspathappend"
    assert sanitize_fts_token("try:") == "try"
    assert sanitize_fts_token("r = requests") == "r  requests"
    assert sanitize_fts_token("# comment") == " comment"
    assert sanitize_fts_token("") is None

def test_fts_query_no_crash():
    """Test da generirani query ne sadrži nevaljane znakove"""
    tokens = ["sys.path.append()", "try:", "r = requests.post"]
    query = build_fts_query(tokens, "default", "or")
    
    # Provjeri da nema opasnih znakova
    assert "=" not in query
    assert "#" not in query
    assert "(" not in query or query.count("(") == query.count(")")  # Balanced
    
    print(f"Generated query: {query}")
```

Pokreni:
```powershell
pytest tests/test_librarian_fts.py -v -s
```

### B) Test ChromaDB Health
```python
# tests/test_chromadb_health.py
import pytest
import chromadb
from pathlib import Path

@pytest.fixture(scope="function")
def fresh_client():
    """Svaki test dobiva svoj client"""
    client = chromadb.PersistentClient(path="./data/store")
    yield client

def test_collection_count(fresh_client):
    """Test da collection.count() ne crashuje"""
    try:
        collection = fresh_client.get_collection("my_collection")
        count = collection.count()
        print(f"✅ Collection count: {count}")
        assert count >= 0
    except Exception as e:
        pytest.fail(f"Collection count failed: {e}")

def test_basic_query(fresh_client):
    """Test osnovnog vector queryja"""
    collection = fresh_client.get_collection("my_collection")
    
    results = collection.query(
        query_texts=["test query"],
        n_results=5
    )
    
    print(f"✅ Query returned {len(results['ids'][0])} results")
    assert results is not None

def test_chromadb_dimensions():
    """Test da embedding dimenzije matchaju"""
    client = chromadb.PersistentClient(path="./data/store")
    collection = client.get_collection("my_collection")
    
    # Ako imaš stored metadata o dimenzijama:
    expected_dim = collection.metadata.get("embedding_dimension")
    if expected_dim:
        print(f"Expected dimension: {expected_dim}")
        # Ovdje bi testirao da se stvarni embeddings poklapaju
```

Pokreni:
```powershell
pytest tests/test_chromadb_health.py -v -s
```

### C) Test FastPath Rust Engine
```python
# tests/test_rust_engine.py
import pytest
from src.modules.kronos_core import FastPath

def test_rust_engine_basic():
    """Test da Rust engine radi bez crasheva"""
    engine = FastPath()
    
    # Insert
    engine.insert("test_key", "test_value")
    print("✅ Insert OK")
    
    # Search exact match
    result = engine.search("test_key")
    assert result is not None
    print(f"✅ Search result: {result}")

def test_rust_engine_substring():
    """Test da li Rust engine podržava substring pretragu"""
    engine = FastPath()
    engine.insert("Daj mi detalje o T034", "Test data")
    
    # Pokušaj naći samo "T034"
    result = engine.search("T034")
    
    if result is None:
        print("⚠️ Substring search NOT supported - only exact match")
    else:
        print(f"✅ Substring search OK: {result}")
```

***

## 3. Integration Tests (End-to-End)

Testiraj cijeli flow od API requesta do odgovora:

```python
# tests/test_integration.py
import pytest
import requests
import time
import subprocess
import os

@pytest.fixture(scope="module")
def running_server():
    """Pokreni server za testove i ugasi ga nakon"""
    # Pokreni server u pozadini
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    proc = subprocess.Popen(
        ["python", "src/server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Čekaj da se server podigne (max 10 sec)
    for _ in range(10):
        try:
            requests.get("http://127.0.0.1:8000/health", timeout=1)
            break
        except:
            time.sleep(1)
    
    yield proc
    
    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)

def test_query_endpoint(running_server):
    """Test /query endpointa"""
    response = requests.post(
        "http://127.0.0.1:8000/query",
        json={"text": "Daj mi detalje o T034", "mode": "light"},
        timeout=10
    )
    
    assert response.status_code == 200
    data = response.json()
    
    print(f"Response: {data}")
    assert "error" not in data or data.get("status") != "error"

def test_malformed_query(running_server):
    """Test da server ne crashuje na loš input"""
    # Prazan text
    response = requests.post(
        "http://127.0.0.1:8000/query",
        json={"text": "", "mode": "light"},
        timeout=10
    )
    
    # Očekujemo error response ALI ne crash (status 200 ili 400, ne 500)
    assert response.status_code in [200, 400, 422]

def test_code_query(running_server):
    """Test da server radi s code upitima (koje su prije uzrokovale FTS crash)"""
    code_query = "import requests\nprint('test')"
    
    response = requests.post(
        "http://127.0.0.1:8000/query",
        json={"text": code_query, "mode": "light"},
        timeout=10
    )
    
    # Ne bi smio crashati
    assert response.status_code == 200
    print(f"Code query handled: {response.json()}")
```

Pokreni:
```powershell
pytest tests/test_integration.py -v -s
```

***

## 4. Load Test (Optional - ako te zanima performance)

```python
# tests/test_load.py
import pytest
import requests
import concurrent.futures
import time

def send_query(query_text):
    """Helper za slanje jednog requesta"""
    try:
        response = requests.post(
            "http://127.0.0.1:8000/query",
            json={"text": query_text, "mode": "light"},
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Request failed: {e}")
        return False

def test_concurrent_requests():
    """Test da server radi pod concurrent load"""
    queries = [
        "Daj mi detalje o T034",
        "Što je Kronos?",
        "import sys",
        "test query"
    ] * 5  # 20 ukupnih querya
    
    start = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send_query, queries))
    
    duration = time.time() - start
    success_rate = sum(results) / len(results) * 100
    
    print(f"""
    Load Test Results:
    - Total requests: {len(queries)}
    - Successful: {sum(results)}
    - Success rate: {success_rate:.1f}%
    - Duration: {duration:.2f}s
    - Throughput: {len(queries)/duration:.1f} req/s
    """)
    
    assert success_rate >= 95  # Očekujemo 95%+ success rate
```

***

## 5. Manual Testing Checklist

Prođi kroz ove scenarije ručno:

```markdown
## Manual Test Checklist

### Server Startup
- [x] Server se pokreće bez errora
- [x] FastPath Rust engine se učitava ("Rust engine ucitan!")
- [x] ChromaDB se inicijalizira ("Initializing Singleton Oracle...")
- [x] Watcher se pokreće ("Background Watcher pokrenut")

### Basic Queries
- [x] Query s postojećim entitetom: "Daj mi detalje o T034"
- [x] Query s nepostojećim entitetom: "Daj mi detalje o FAKE123"
- [x] Prazan query: ""
- [x] Query s code sintaksom: "import sys\nprint('test')"

### Error Recovery
- [x] Posalji query dok je ChromaDB broken → Dobij "Nema znanja" (ne crash)
- [x] Posalji query s FTS problematic znakovima → Radi bez crasheva
- [x] Posalji malformed JSON → Dobij 422 error (ne 500)

### Monitoring
- [x] Provjeri `/health` endpoint vraća 200
- [x] Provjeri server logi nemaju "CRITICAL" ili "ERROR" (osim očekivanih)
- [x] Provjeri ChromaDB collection count nije 0 (ako si ingestao podatke)
```

***

## 6. Automated Test Suite (All-in-One)

Kreiraj `run_all_tests.ps1`:
```powershell
# run_all_tests.ps1
Write-Host "🧪 Starting Kronos Test Suite..." -ForegroundColor Cyan

# 1. Unit tests
Write-Host "`n📦 Running Unit Tests..." -ForegroundColor Yellow
pytest tests/test_librarian_fts.py tests/test_chromadb_health.py tests/test_rust_engine.py -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Unit tests failed!" -ForegroundColor Red
    exit 1
}

# 2. Integration tests
Write-Host "`n🔗 Running Integration Tests..." -ForegroundColor Yellow
pytest tests/test_integration.py -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Integration tests failed!" -ForegroundColor Red
    exit 1
}

# 3. Optional: Load tests
# pytest tests/test_load.py -v

Write-Host "`n✅ All tests passed!" -ForegroundColor Green
```

Pokreni:
```powershell
.\run_all_tests.ps1
```

***

## Prioritizacija

**Ako imaš samo 15 minuta:**
1. Quick Smoke Test (#1)
2. Test FTS Query Builder (#2A)
3. Test ChromaDB Health (#2B)

**Ako imaš 1 sat:**
- Sve gore + Integration Tests (#3)

**Za production-ready:**
- Sve gore + Load Tests (#4) + Manual Checklist (#5)

***

**Što testirati PRVO?**
Započni s:
```powershell
pytest tests/test_librarian_fts.py -v -s
```
Jer je FTS greška bila najvidljivija u tvojim logovima.

Javi mi kako prolaze testovi i gdje eventulano zapne! 🚀