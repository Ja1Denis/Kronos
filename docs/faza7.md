# FAZA 7: INTEGRATION SA ANTIGRAVITY - Detaljni Taskovi za Gemini Flash

**NAPOMENA ZA FLASH:** Ova faza integrira Kronos pointer system sa Antigravity glavnim AI agentom. Pročitaj SVE zadatke prije nego počneš kodirati.

***

## FAZA 7.0: PRE-INTEGRATION AUDIT

### Task 7.0.1: Map Antigravity Architecture
**CILJ:** Razumjeti postojeću strukturu prije modifikacije

- [ ] **Locate Antigravity codebase:**
  - Pronađi root folder: `E:\G\GeminiCLI\ai-test-project\antigravity\` (ili gdje god je)
  - List all directories: Zapiši strukturu foldera
  - Identify entry point: Koji je main file? (`main.py`, `server.py`, `app.py`?)
  
- [ ] **Document current Kronos integration:**
  - Grep za "kronos" u Antigravity kodu: `grep -r "kronos" ./antigravity`
  - Pronađi gdje se trenutno poziva Kronos
  - Zapiši current API calls:
    - Koja funkcija poziva?
    - Koji endpoint-i se koriste?
    - Kako se šalju parametri?
  
- [ ] **Identify HTTP client library:**
  - Provjeri `requirements.txt` ili `package.json`
  - Koristi li: `requests`, `httpx`, `aiohttp`, `fetch`, `axios`?
  - Zapiši: Library name + version
  
- [ ] **Find where context is built:**
  - Pronađi funkciju koja priprema context za LLM
  - Kako se formatira? (string concatenation, list of messages, JSON?)
  - Koliki je max context size? (provjeri u config-u)
  
- [ ] **Document LLM integration:**
  - Koji model se koristi? (GPT-4, Gemini, Claude, local?)
  - Kako se poziva? (OpenAI SDK, Google AI SDK, HTTP direct?)
  - Gdje je system prompt? (file path)

**OUTPUT:** Kreiraj file `docs/ANTIGRAVITY_ARCHITECTURE.md` sa svim findings.

**⚠️ FLASH WARNING:** NE pretpostavljaj ništa. Ako ne možeš naći nešto, dokumentiraj "NOT FOUND" i pitaj.

***

### Task 7.0.2: Create Integration Test Environment
**CILJ:** Setup gdje možeš testirati Antigravity ↔ Kronos komunikaciju

- [ ] **Ensure Kronos is running:**
  - Pokreni Kronos server: `python src/server.py`
  - Verifikuj: `curl http://localhost:8000/health`
  - Trebao bi return: `{"status": "ok", ...}`
  
- [ ] **Test existing /query endpoint:**
  - Manual test: `curl -X POST http://localhost:8000/query -d '{"text": "test"}'`
  - Zapiši response format
  - Verifikuj: Vraća li pointere u novom formatu ili stari format?
  
- [ ] **Test new /fetch_exact endpoint:**
  - Index neki test fajl (ako već nije)
  - Manual test:
    ```bash
    curl -X POST http://localhost:8000/fetch_exact \
      -H "Content-Type: application/json" \
      -d '{
        "session_id": "test123",
        "file_path": "path/to/test.md",
        "start_line": 0,
        "end_line": 10
      }'
    ```
  - Verifikuj: Vraća li content ili error?
  
- [ ] **Create mock responses:**
  - Kreiraj `tests/fixtures/kronos_responses.json`
  - Mock pointer response:
    ```json
    {
      "type": "pointer_response",
      "pointers": [
        {
          "file_path": "test.md",
          "section": "Test Section",
          "line_range": [0, 10],
          "keywords": ["test", "example"],
          "confidence": 0.85
        }
      ],
      "total_found": 1
    }
    ```
  - Mock fetch_exact response:
    ```json
    {
      "content": "This is test content...",
      "lines_read": 10,
      "file_path": "test.md"
    }
    ```

**⚠️ FLASH WARNING:** Svaki curl test MORA uspjeti prije nego nastaviš. Ako faila, ne nastavljaj dalje.

***

## FAZA 7.1: ANTIGRAVITY API CLIENT

### Task 7.1.1: Create Kronos Client Module
**CILJ:** Centralizovani modul za sve Kronos API pozive

- [ ] **Determine file location:**
  - Ako Antigravity ima `clients/` ili `api/` folder → tamo
  - Ako ne: Kreiraj `antigravity/clients/` folder
  - Kreiraj file: `antigravity/clients/kronos_client.py`

- [ ] **Import dependencies:**
  ```python
  # OBAVEZNO: Ovi importi
  import httpx  # Ili 'requests' ako httpx nije dostupan
  import logging
  from typing import Optional, Dict, List, Any
  from dataclasses import dataclass
  import time
  
  logger = logging.getLogger(__name__)
  ```

- [ ] **Define data classes for type safety:**
  ```python
  # OBAVEZNO: Definiši prije client classa
  
  @dataclass
  class Pointer:
      """Lightweight reference to document location"""
      file_path: str
      section: str
      line_range: tuple[int, int]
      keywords: list[str]
      confidence: float
      last_modified: str = ""
      content_hash: str = ""
      indexed_at: str = ""
      
      @classmethod
      def from_dict(cls, data: dict):
          """DEFENSIVE: Safe construction from API response"""
          try:
              return cls(
                  file_path=data.get('file_path', 'unknown'),
                  section=data.get('section', 'Untitled'),
                  line_range=tuple(data.get('line_range', [0, 0])),
                  keywords=data.get('keywords', []),
                  confidence=float(data.get('confidence', 0.0)),
                  last_modified=data.get('last_modified', ''),
                  content_hash=data.get('content_hash', ''),
                  indexed_at=data.get('indexed_at', '')
              )
          except Exception as e:
              logger.error(f"Failed to parse Pointer: {e}")
              # Return minimal valid pointer instead of crash
              return cls(
                  file_path='unknown',
                  section='Parse Error',
                  line_range=(0, 0),
                  keywords=[],
                  confidence=0.0
              )
  
  @dataclass
  class QueryResponse:
      """Response from /query endpoint"""
      type: str  # "pointer_response", "chunk_response", "mixed_response"
      pointers: List[Pointer]
      chunks: List[Dict[str, Any]]
      message: str = ""
      total_found: int = 0
  
  @dataclass
  class FetchExactResponse:
      """Response from /fetch_exact endpoint"""
      content: str
      lines_read: int
      file_path: str
      warning: Optional[str] = None
      error: Optional[str] = None
  ```

**⚠️ FLASH WARNING:** 
- `from_dict()` metoda MORA handlati missing fields
- NE crashuj ako API vrati unexpected format
- Return fallback values umjesto None

***

### Task 7.1.2: Implement KronosClient Class
**CILJ:** Client sa retry logic, error handling, timeout

- [ ] **Define class with configuration:**
  ```python
  class KronosClient:
      """
      Client for communicating with Kronos search service.
      
      Features:
      - Automatic retry with exponential backoff
      - Request/response logging
      - Error handling with graceful degradation
      - Connection pooling
      """
      
      def __init__(
          self,
          base_url: str = "http://localhost:8000",
          timeout: int = 30,
          max_retries: int = 3,
          session_id: Optional[str] = None
      ):
          """
          DEFENSIVE: All parameters have defaults
          """
          self.base_url = base_url.rstrip('/')  # Remove trailing slash
          self.timeout = timeout
          self.max_retries = max_retries
          self.session_id = session_id or self._generate_session_id()
          
          # HTTP client with connection pooling
          self.client = httpx.Client(
              timeout=timeout,
              limits=httpx.Limits(max_keepalive_connections=5)
          )
          
          logger.info(f"KronosClient initialized: {base_url}, session={self.session_id}")
      
      def _generate_session_id(self) -> str:
          """Generate unique session ID"""
          import uuid
          return f"antigravity_{uuid.uuid4().hex[:8]}"
      
      def __enter__(self):
          return self
      
      def __exit__(self, exc_type, exc_val, exc_tb):
          self.client.close()
  ```

**⚠️ FLASH WARNING:**
- `base_url.rstrip('/')` je OBAVEZAN (spriječava double slash u URL-u)
- `__enter__` i `__exit__` omogućavaju `with KronosClient() as client:`
- Session ID mora biti unique per conversation

***

### Task 7.1.3: Implement Query Method with Retry Logic
**CILJ:** Robust query method koji ne faila lako

- [ ] **Implement query() method:**
  ```python
  def query(
      self,
      text: str,
      limit: int = 4000,
      silent: bool = True
  ) -> Optional[QueryResponse]:
      """
      Query Kronos for relevant information.
      
      Args:
          text: Search query
          limit: Token budget limit
          silent: Suppress verbose logging
      
      Returns:
          QueryResponse object or None if failed
      
      DEFENSIVE: Retries on failure, returns None instead of crash
      """
      
      # VALIDATION
      if not text or not isinstance(text, str):
          logger.error(f"Invalid query text: {text}")
          return None
      
      if len(text.strip()) == 0:
          logger.warning("Empty query text")
          return None
      
      # Prepare request
      url = f"{self.base_url}/query"
      payload = {
          "text": text.strip(),
          "limit": limit,
          "silent": silent,
          "session_id": self.session_id  # Track session
      }
      
      # RETRY LOOP with exponential backoff
      last_error = None
      
      for attempt in range(1, self.max_retries + 1):
          try:
              logger.debug(f"Query attempt {attempt}/{self.max_retries}: {text[:50]}...")
              
              response = self.client.post(url, json=payload)
              
              # Check status code
              if response.status_code == 200:
                  data = response.json()
                  return self._parse_query_response(data)
              
              elif response.status_code == 500:
                  logger.error(f"Kronos server error (500): {response.text}")
                  last_error = "Server error"
                  # Retry on 500
              
              elif response.status_code == 404:
                  logger.error(f"Endpoint not found (404): {url}")
                  return None  # Don't retry on 404
              
              else:
                  logger.warning(f"Unexpected status {response.status_code}: {response.text}")
                  last_error = f"HTTP {response.status_code}"
          
          except httpx.ConnectError:
              logger.error(f"Cannot connect to Kronos at {self.base_url}")
              last_error = "Connection refused"
          
          except httpx.TimeoutException:
              logger.error(f"Kronos timeout after {self.timeout}s")
              last_error = "Timeout"
          
          except Exception as e:
              logger.error(f"Unexpected error querying Kronos: {e}", exc_info=True)
              last_error = str(e)
          
          # Exponential backoff before retry
          if attempt < self.max_retries:
              sleep_time = 2 ** attempt  # 2s, 4s, 8s
              logger.info(f"Retrying in {sleep_time}s...")
              time.sleep(sleep_time)
      
      # All retries failed
      logger.error(f"Query failed after {self.max_retries} attempts: {last_error}")
      return None
  ```

**⚠️ FLASH WARNING:**
- VALIDATION na vrhu - provjeri text prije slanja
- Retry samo na 500 i network errors (NE na 404)
- Exponential backoff: 2s, 4s, 8s (ne instant retry)
- Return `None` umjesto Exception (graceful degradation)
- Log SVAKI error sa context-om

***

### Task 7.1.4: Implement Response Parser
**CILJ:** Bezbjedno parsiranje API response-a

- [ ] **Implement _parse_query_response():**
  ```python
  def _parse_query_response(self, data: dict) -> Optional[QueryResponse]:
      """
      Parse /query response into QueryResponse object.
      
      DEFENSIVE: Handles missing fields, invalid types
      """
      
      # VALIDATION: Check data is dict
      if not isinstance(data, dict):
          logger.error(f"Invalid response type: {type(data)}")
          return None
      
      try:
          # Extract type
          response_type = data.get('type', 'unknown')
          
          # Parse pointers (if present)
          pointers = []
          if 'pointers' in data and isinstance(data['pointers'], list):
              for p_data in data['pointers']:
                  pointer = Pointer.from_dict(p_data)
                  pointers.append(pointer)
          
          # Parse chunks (if present)
          chunks = []
          if 'chunks' in data and isinstance(data['chunks'], list):
              chunks = data['chunks']
          
          # FALLBACK: If neither pointers nor chunks, check legacy format
          if not pointers and not chunks:
              # Maybe old format returned raw results?
              if 'results' in data:
                  logger.warning("Detected legacy response format, converting...")
                  chunks = data.get('results', [])
          
          return QueryResponse(
              type=response_type,
              pointers=pointers,
              chunks=chunks,
              message=data.get('message', ''),
              total_found=data.get('total_found', len(pointers) + len(chunks))
          )
      
      except Exception as e:
          logger.error(f"Failed to parse query response: {e}", exc_info=True)
          return None
  ```

**⚠️ FLASH WARNING:**
- Provjeri `isinstance(data, dict)` PRIJE pristupa
- Svaki `data.get()` ima fallback default
- Handle legacy format (compatibility)
- Ne crashuj - return None i logiraj error

***

### Task 7.1.5: Implement fetch_exact Method
**CILJ:** Fetch exact file content based on pointer

- [ ] **Implement fetch_exact():**
  ```python
  def fetch_exact(
      self,
      pointer: Pointer,
      verify_hash: bool = True
  ) -> Optional[FetchExactResponse]:
      """
      Fetch exact content from file location.
      
      Args:
          pointer: Pointer object with file location
          verify_hash: Whether to send content_hash for verification
      
      Returns:
          FetchExactResponse or None if failed
      
      DEFENSIVE: Validates pointer before sending, handles all errors
      """
      
      # VALIDATION: Check pointer validity
      if not isinstance(pointer, Pointer):
          logger.error(f"Invalid pointer type: {type(pointer)}")
          return None
      
      if not pointer.file_path or pointer.file_path == 'unknown':
          logger.error("Cannot fetch pointer with unknown file_path")
          return None
      
      if pointer.line_range < 0 or pointer.line_range <= pointer.line_range:
          logger.error(f"Invalid line range: {pointer.line_range}")
          return None
      
      # Prepare request
      url = f"{self.base_url}/fetch_exact"
      payload = {
          "session_id": self.session_id,
          "file_path": pointer.file_path,
          "start_line": pointer.line_range,
          "end_line": pointer.line_range
      }
      
      # Optionally include content_hash for verification
      if verify_hash and pointer.content_hash:
          payload["content_hash"] = pointer.content_hash
      
      # SINGLE ATTEMPT (no retry for fetch - it's deterministic)
      try:
          logger.debug(f"Fetching: {pointer.file_path} lines {pointer.line_range}")
          
          response = self.client.post(url, json=payload, timeout=10)  # Shorter timeout
          
          if response.status_code == 200:
              data = response.json()
              return self._parse_fetch_response(data)
          
          elif response.status_code == 404:
              logger.error(f"File not found: {pointer.file_path}")
              return FetchExactResponse(
                  content="",
                  lines_read=0,
                  file_path=pointer.file_path,
                  error="file_not_found"
              )
          
          else:
              logger.error(f"Fetch failed ({response.status_code}): {response.text}")
              return None
      
      except httpx.TimeoutException:
          logger.error("Fetch timeout (file too large or slow I/O)")
          return None
      
      except Exception as e:
          logger.error(f"Fetch error: {e}", exc_info=True)
          return None
  ```

**⚠️ FLASH WARNING:**
- Validate pointer PRIJE slanja requesta
- Ne retry fetch (ako faila, odmah return)
- Timeout kraći (10s) jer je file read brz
- Return error response umjesto None gdje moguće (više info)

***

### Task 7.1.6: Implement Fetch Response Parser
**CILJ:** Parse fetch_exact response sa error handling

- [ ] **Implement _parse_fetch_response():**
  ```python
  def _parse_fetch_response(self, data: dict) -> Optional[FetchExactResponse]:
      """
      Parse /fetch_exact response.
      
      DEFENSIVE: Handles errors, warnings, edge cases
      """
      
      if not isinstance(data, dict):
          logger.error(f"Invalid fetch response type: {type(data)}")
          return None
      
      # Check for error in response
      if 'error' in data:
          logger.warning(f"Fetch returned error: {data['error']}")
          return FetchExactResponse(
              content="",
              lines_read=0,
              file_path=data.get('file_path', 'unknown'),
              error=data['error']
          )
      
      # Extract content
      content = data.get('content', '')
      
      # Check for warning (stale pointer)
      warning = data.get('warning')
      if warning:
          logger.info(f"Fetch warning: {warning}")
      
      return FetchExactResponse(
          content=content,
          lines_read=data.get('lines_read', 0),
          file_path=data.get('file_path', 'unknown'),
          warning=warning,
          error=None
      )
  ```

**⚠️ FLASH WARNING:**
- Provjeri 'error' field PRVO (prije pristupa 'content')
- Warning nije fatal - return response sa warning-om
- Default values za sve fields

***

### Task 7.1.7: Add Health Check Method
**CILJ:** Provjera da li je Kronos online prije main querija

- [ ] **Implement health_check():**
  ```python
  def health_check(self) -> bool:
      """
      Check if Kronos service is available.
      
      Returns:
          True if healthy, False otherwise
      
      Use this before critical operations.
      """
      try:
          url = f"{self.base_url}/health"
          response = self.client.get(url, timeout=5)
          
          if response.status_code == 200:
              data = response.json()
              status = data.get('status', 'unknown')
              
              if status == 'ok':
                  logger.info("Kronos health check: OK")
                  return True
              else:
                  logger.warning(f"Kronos unhealthy: {status}")
                  return False
          else:
              logger.error(f"Health check failed: {response.status_code}")
              return False
      
      except Exception as e:
          logger.error(f"Health check error: {e}")
          return False
  ```

**⚠️ FLASH WARNING:**
- Timeout 5s (health check mora biti brz)
- Return `False` na bilo koji error (ne crashuj)

***

### Task 7.1.8: Add Unit Tests for KronosClient
**CILJ:** Test client functionality u izolaciji

- [ ] **Create test file:** `tests/test_kronos_client.py`
- [ ] **Setup test fixtures:**
  ```python
  import pytest
  from unittest.mock import Mock, patch
  from antigravity.clients.kronos_client import KronosClient, Pointer
  
  @pytest.fixture
  def mock_response_pointer():
      """Mock pointer response from /query"""
      return {
          "type": "pointer_response",
          "pointers": [
              {
                  "file_path": "test.md",
                  "section": "Test",
                  "line_range": [0, 10],
                  "keywords": ["test"],
                  "confidence": 0.9
              }
          ],
          "total_found": 1
      }
  
  @pytest.fixture
  def mock_response_fetch():
      """Mock response from /fetch_exact"""
      return {
          "content": "Test content here",
          "lines_read": 10,
          "file_path": "test.md"
      }
  ```

- [ ] **Test query() success:**
  ```python
  def test_query_success(mock_response_pointer):
      with patch('httpx.Client.post') as mock_post:
          # Setup mock
          mock_post.return_value = Mock(
              status_code=200,
              json=lambda: mock_response_pointer
          )
          
          # Test
          client = KronosClient()
          result = client.query("test query")
          
          # Assert
          assert result is not None
          assert result.type == "pointer_response"
          assert len(result.pointers) == 1
          assert result.pointers.file_path == "test.md"
  ```

- [ ] **Test query() retry on 500:**
  ```python
  def test_query_retries_on_500():
      with patch('httpx.Client.post') as mock_post:
          # First two calls return 500, third succeeds
          mock_post.side_effect = [
              Mock(status_code=500, text="Server error"),
              Mock(status_code=500, text="Server error"),
              Mock(status_code=200, json=lambda: {"type": "pointer_response", "pointers": []})
          ]
          
          with patch('time.sleep'):  # Mock sleep to speed up test
              client = KronosClient(max_retries=3)
              result = client.query("test")
              
              # Should succeed on 3rd attempt
              assert result is not None
              assert mock_post.call_count == 3
  ```

- [ ] **Test query() fails after max retries:**
  ```python
  def test_query_fails_after_max_retries():
      with patch('httpx.Client.post') as mock_post:
          mock_post.return_value = Mock(status_code=500, text="Error")
          
          with patch('time.sleep'):
              client = KronosClient(max_retries=2)
              result = client.query("test")
              
              # Should return None after 2 retries
              assert result is None
              assert mock_post.call_count == 2
  ```

- [ ] **Test fetch_exact() success:**
  ```python
  def test_fetch_exact_success(mock_response_fetch):
      with patch('httpx.Client.post') as mock_post:
          mock_post.return_value = Mock(
              status_code=200,
              json=lambda: mock_response_fetch
          )
          
          pointer = Pointer(
              file_path="test.md",
              section="Test",
              line_range=(0, 10),
              keywords=["test"],
              confidence=0.9
          )
          
          client = KronosClient()
          result = client.fetch_exact(pointer)
          
          assert result is not None
          assert result.content == "Test content here"
          assert result.error is None
  ```

- [ ] **Test fetch_exact() with invalid pointer:**
  ```python
  def test_fetch_exact_invalid_pointer():
      pointer = Pointer(
          file_path="unknown",  # Invalid
          section="Test",
          line_range=(0, 10),
          keywords=[],
          confidence=0.0
      )
      
      client = KronosClient()
      result = client.fetch_exact(pointer)
      
      # Should return None (validation failed)
      assert result is None
  ```

- [ ] **Test health_check():**
  ```python
  def test_health_check_ok():
      with patch('httpx.Client.get') as mock_get:
          mock_get.return_value = Mock(
              status_code=200,
              json=lambda: {"status": "ok"}
          )
          
          client = KronosClient()
          assert client.health_check() is True
  
  def test_health_check_failed():
      with patch('httpx.Client.get') as mock_get:
          mock_get.side_effect = Exception("Connection refused")
          
          client = KronosClient()
          assert client.health_check() is False
  ```

**⚠️ FLASH WARNING:**
- SVAKI test mora proći prije nego nastaviš
- Mock `time.sleep` da testovi budu brzi
- Test both success AND failure paths

***

## FAZA 7.2: SMART POINTER RESOLUTION

### Task 7.2.1: Create Pointer Resolution Strategy
**CILJ:** Odluči koje pointere fetchati na osnovu budgeta

- [ ] **Create file:** `antigravity/services/pointer_resolver.py`
- [ ] **Import dependencies:**
  ```python
  import logging
  from typing import List, Dict, Optional, Tuple
  from dataclasses import dataclass
  from antigravity.clients.kronos_client import KronosClient, Pointer, FetchExactResponse
  
  logger = logging.getLogger(__name__)
  ```

- [ ] **Define resolution result:**
  ```python
  @dataclass
  class ResolutionResult:
      """Result of pointer resolution process"""
      context: str  # Combined context string for LLM
      pointers_fetched: int
      pointers_skipped: int
      tokens_used: int
      warnings: List[str]
      
      def has_content(self) -> bool:
          """Check if any content was retrieved"""
          return len(self.context.strip()) > 0
  ```

- [ ] **Define token estimator:**
  ```python
  class TokenEstimator:
      """
      Estimate token count from text.
      
      CONSERVATIVE: Over-estimates to avoid budget overrun.
      """
      
      # File type specific ratios (tokens per character)
      FILE_TYPE_RATIOS = {
          '.md': 0.30,   # Markdown (verbose)
          '.py': 0.25,   # Python code
          '.json': 0.20, # JSON (compact)
          '.txt': 0.28,  # Plain text
          '.yml': 0.22,  # YAML
          'default': 0.27
      }
      
      @staticmethod
      def estimate(text: str, file_path: str = "") -> int:
          """
          Estimate token count.
          
          DEFENSIVE: Always over-estimate by 20% safety margin
          """
          if not text:
              return 0
          
          # Determine file type
          import os
          ext = os.path.splitext(file_path).lower() if file_path else 'default'
          ratio = TokenEstimator.FILE_TYPE_RATIOS.get(ext, TokenEstimator.FILE_TYPE_RATIOS['default'])
          
          # Base estimate
          estimated = len(text) * ratio
          
          # Safety margin (20% overhead)
          estimated *= 1.2
          
          # Round up
          return int(estimated) + 1
      
      @staticmethod
      def estimate_line_range(line_range: Tuple[int, int], file_path: str = "") -> int:
          """
          Estimate tokens without fetching content.
          
          Assumes average 80 characters per line.
          """
          line_count = line_range - line_range
          avg_chars_per_line = 80
          estimated_chars = line_count * avg_chars_per_line
          
          # Apply file type ratio
          import os
          ext = os.path.splitext(file_path).lower() if file_path else 'default'
          ratio = TokenEstimator.FILE_TYPE_RATIOS.get(ext, TokenEstimator.FILE_TYPE_RATIOS['default'])
          
          estimated = estimated_chars * ratio * 1.2  # With safety margin
          
          return int(estimated) + 1
  ```

**⚠️ FLASH WARNING:**
- Token estimation je ART, ne science
- UVIJEK over-estimate (bolje nego budget overflow)
- Safety margin 20% je minimum

***

### Task 7.2.2: Implement Pointer Resolver Class
**CILJ:** Main logic za pointer resolution

- [ ] **Implement PointerResolver class:**
  ```python
  class PointerResolver:
      """
      Resolves pointers into context string while respecting token budget.
      
      Strategy:
      1. Sort pointers by confidence (descending)
      2. Estimate token cost before fetching
      3. Fetch highest confidence pointers first
      4. Stop when budget would be exceeded
      5. Keep remaining as pointer references
      """
      
      def __init__(
          self,
          kronos_client: KronosClient,
          budget: int = 4000,
          pointer_metadata_tokens: int = 100
      ):
          """
          Args:
              kronos_client: Initialized Kronos client
              budget: Total token budget for context
              pointer_metadata_tokens: Tokens per pointer metadata (avg)
          """
          self.client = kronos_client
          self.budget = budget
          self.pointer_metadata_tokens = pointer_metadata_tokens
          self.estimator = TokenEstimator()
          
          logger.info(f"PointerResolver initialized with budget={budget}")
      
      def resolve(
          self,
          pointers: List[Pointer],
          fetch_strategy: str = "selective"
      ) -> ResolutionResult:
          """
          Resolve pointers into context string.
          
          Args:
              pointers: List of pointers to resolve
              fetch_strategy: 
                  - "selective": Fetch based on budget (default)
                  - "all": Try to fetch all (may exceed budget)
                  - "none": Don't fetch any, return pointer metadata only
          
          Returns:
              ResolutionResult with context and metadata
          
          DEFENSIVE: Never crashes, returns partial result on error
          """
          
          if not pointers:
              logger.warning("No pointers to resolve")
              return ResolutionResult(
                  context="",
                  pointers_fetched=0,
                  pointers_skipped=0,
                  tokens_used=0,
                  warnings=["No pointers provided"]
              )
          
          # Strategy dispatch
          if fetch_strategy == "none":
              return self._metadata_only(pointers)
          elif fetch_strategy == "all":
              return self._fetch_all(pointers)
          else:  # "selective" (default)
              return self._fetch_selective(pointers)
  ```

**⚠️ FLASH WARNING:**
- Default strategy je "selective" (pametno odabira)
- Mora podržati sve 3 strategije
- Ne crashuj na prazan input - return empty result

***

### Task 7.2.3: Implement Selective Fetch Strategy
**CILJ:** Fetch samo što stane u budget, prioritiziraj visok confidence

- [ ] **Implement _fetch_selective():**
  ```python
  def _fetch_selective(self, pointers: List[Pointer]) -> ResolutionResult:
      """
      Selectively fetch pointers based on budget and confidence.
      
      Algorithm:
      1. Sort by confidence (high to low)
      2. Reserve space for pointer metadata
      3. Fetch pointers incrementally
      4. Stop when budget exhausted
      5. Keep remaining as references
      
      DEFENSIVE: Tracks budget accurately, never exceeds
      """
      
      context_parts = []
      tokens_used = 0
      fetched_count = 0
      skipped_count = 0
      warnings = []
      
      # Sort by confidence (descending)
      sorted_pointers = sorted(pointers, key=lambda p: p.confidence, reverse=True)
      
      # Reserve budget for pointer metadata overhead
      metadata_overhead = len(pointers) * self.pointer_metadata_tokens
      available_budget = self.budget - metadata_overhead
      
      if available_budget < 0:
          logger.error(f"Too many pointers ({len(pointers)}) for budget ({self.budget})")
          warnings.append(f"Pointer count ({len(pointers)}) exceeds budget capacity")
          # Fall back to metadata only
          return self._metadata_only(pointers[:10])  # Limit to 10
      
      logger.info(f"Resolving {len(pointers)} pointers, budget={self.budget}, available={available_budget}")
      
      # Process each pointer
      for i, pointer in enumerate(sorted_pointers):
          logger.debug(f"[{i+1}/{len(pointers)}] Processing: {pointer.file_path} (conf={pointer.confidence:.2f})")
          
          # Estimate cost BEFORE fetching
          estimated_tokens = self.estimator.estimate_line_range(
              pointer.line_range,
              pointer.file_path
          )
          
          # Check budget
          if tokens_used + estimated_tokens > available_budget:
              logger.info(f"Budget exhausted ({tokens_used}+{estimated_tokens} > {available_budget}), switching to metadata")
              # Add remaining as metadata references
              remaining = sorted_pointers[i:]
              metadata_part = self._format_pointer_metadata(remaining)
              context_parts.append(metadata_part)
              skipped_count += len(remaining)
              break
          
          # Fetch content
          fetch_result = self.client.fetch_exact(pointer, verify_hash=True)
          
          if fetch_result is None:
              # Fetch failed, skip this pointer
              logger.warning(f"Failed to fetch: {pointer.file_path}")
              warnings.append(f"Fetch failed: {pointer.file_path}")
              skipped_count += 1
              continue
          
          if fetch_result.error:
              # Error in fetch (e.g., file not found)
              logger.warning(f"Fetch error: {fetch_result.error}")
              warnings.append(f"{pointer.file_path}: {fetch_result.error}")
              skipped_count += 1
              continue
          
          # Success - add to context
          content = fetch_result.content
          actual_tokens = self.estimator.estimate(content, pointer.file_path)
          
          # Format content with header
          formatted = self._format_fetched_content(pointer, content, fetch_result.warning)
          context_parts.append(formatted)
          
          tokens_used += actual_tokens
          fetched_count += 1
          
          logger.debug(f"Fetched: {actual_tokens} tokens (total: {tokens_used}/{available_budget})")
      
      # Combine all parts
      final_context = "\n\n---\n\n".join(context_parts)
      
      # Final token count
      final_tokens = self.estimator.estimate(final_context)
      
      logger.info(f"Resolution complete: fetched={fetched_count}, skipped={skipped_count}, tokens={final_tokens}")
      
      return ResolutionResult(
          context=final_context,
          pointers_fetched=fetched_count,
          pointers_skipped=skipped_count,
          tokens_used=final_tokens,
          warnings=warnings
      )
  ```

**⚠️ FLASH WARNING:**
- Budget tracking je KRITIČAN - prati svaki token
- Reserve metadata overhead PRIJE nego počneš fetchat
- Ne fetchaj ako bi premaš budget (check PRIJE, ne POSLIJE)
- Log svaki decision (za debugging)
- Handle errors gracefully (skip pointer, nastavi dalje)

***

### Task 7.2.4: Implement Formatting Helpers
**CILJ:** Formatiraj content i metadata za LLM

- [ ] **Implement formatters:**
  ```python
  def _format_fetched_content(
      self,
      pointer: Pointer,
      content: str,
      warning: Optional[str] = None
  ) -> str:
      """
      Format fetched content with header.
      
      Output example:
      ## 📄 development_log.md (Lines 145-160)
      **Section:** Release v0.2.62
      **Confidence:** 0.85
      [⚠️ Warning: File modified since indexing]
      
      [actual content here]
      """
      
      header = f"## 📄 {pointer.file_path} (Lines {pointer.line_range}-{pointer.line_range})\n"
      header += f"**Section:** {pointer.section}\n"
      header += f"**Confidence:** {pointer.confidence:.2f}\n"
      
      if warning:
          header += f"\n⚠️ **Warning:** {warning}\n"
      
      return f"{header}\n{content}"
  
  def _format_pointer_metadata(self, pointers: List[Pointer]) -> str:
      """
      Format pointers as metadata references (not fetched).
      
      Output example:
      ## 📍 Additional Relevant Locations
      
      1. **test.md** (Lines 10-20) - Section: "Testing"
         Keywords: test, example, demo
         Confidence: 0.75
      
      2. **docs/api.md** (Lines 50-60) - Section: "API Reference"
         Keywords: api, endpoint, request
         Confidence: 0.68
      """
      
      if not pointers:
          return ""
      
      lines = ["## 📍 Additional Relevant Locations\n"]
      
      for i, p in enumerate(pointers, 1):
          lines.append(f"{i}. **{p.file_path}** (Lines {p.line_range}-{p.line_range}) - Section: \"{p.section}\"")
          lines.append(f"   Keywords: {', '.join(p.keywords[:5])}")  # Limit to 5 keywords
          lines.append(f"   Confidence: {p.confidence:.2f}\n")
      
      return "\n".join(lines)
  ```

**⚠️ FLASH WARNING:**
- Format mora biti LLM-friendly (structured, clear headers)
- Warning mora biti prominentan ako postoji
- Keywords limit na 5 (ne preopterećuj sa keyword-ima)

***

### Task 7.2.5: Implement Metadata-Only Strategy
**CILJ:** Fallback kada ne možeš fetchat content

- [ ] **Implement _metadata_only():**
  ```python
  def _metadata_only(self, pointers: List[Pointer]) -> ResolutionResult:
      """
      Return only pointer metadata without fetching content.
      
      Use when:
      - fetch_strategy = "none"
      - Budget too small for any fetch
      - All fetches failed
      
      DEFENSIVE: Always succeeds
      """
      
      if not pointers:
          return ResolutionResult(
              context="",
              pointers_fetched=0,
              pointers_skipped=0,
              tokens_used=0,
              warnings=["No pointers to display"]
          )
      
      # Limit to top 10 by confidence
      top_pointers = sorted(pointers, key=lambda p: p.confidence, reverse=True)[:10]
      
      context = self._format_pointer_metadata(top_pointers)
      tokens = self.estimator.estimate(context)
      
      logger.info(f"Metadata-only resolution: {len(top_pointers)} pointers, {tokens} tokens")
      
      return ResolutionResult(
          context=context,
          pointers_fetched=0,
          pointers_skipped=len(pointers),
          tokens_used=tokens,
          warnings=[f"No content fetched (metadata only for {len(top_pointers)} locations)"]
      )
  ```

**⚠️ FLASH WARNING:**
- Limit na 10 pointera (ne preopterećuj LLM sa 100 referenci)
- Sort by confidence UVIJEK

***

### Task 7.2.6: Implement Fetch-All Strategy
**CILJ:** Pokušaj fetcha sve (za high-budget scenarije)

- [ ] **Implement _fetch_all():**
  ```python
  def _fetch_all(self, pointers: List[Pointer]) -> ResolutionResult:
      """
      Attempt to fetch all pointers.
      
      WARNING: May exceed budget! Use only when budget is very high.
      
      DEFENSIVE: Tracks budget, stops if overrun imminent
      """
      
      context_parts = []
      tokens_used = 0
      fetched_count = 0
      skipped_count = 0
      warnings = []
      
      # Sort by confidence anyway (fetch best first)
      sorted_pointers = sorted(pointers, key=lambda p: p.confidence, reverse=True)
      
      for pointer in sorted_pointers:
          # Emergency brake: Stop if 90% budget used
          if tokens_used > self.budget * 0.9:
              logger.warning(f"Emergency stop at 90% budget ({tokens_used}/{self.budget})")
              warnings.append("Budget limit reached, stopped fetching")
              remaining = len(sorted_pointers) - fetched_count - skipped_count
              skipped_count += remaining
              break
          
          # Fetch
          fetch_result = self.client.fetch_exact(pointer, verify_hash=True)
          
          if fetch_result and not fetch_result.error:
              content = fetch_result.content
              formatted = self._format_fetched_content(pointer, content, fetch_result.warning)
              context_parts.append(formatted)
              
              tokens = self.estimator.estimate(content, pointer.file_path)
              tokens_used += tokens
              fetched_count += 1
          else:
              skipped_count += 1
              if fetch_result:
                  warnings.append(f"{pointer.file_path}: {fetch_result.error}")
      
      final_context = "\n\n---\n\n".join(context_parts)
      final_tokens = self.estimator.estimate(final_context)
      
      if final_tokens > self.budget:
          warnings.append(f"Budget exceeded! {final_tokens} > {self.budget}")
          logger.warning(f"Budget overrun: {final_tokens} > {self.budget}")
      
      return ResolutionResult(
          context=final_context,
          pointers_fetched=fetched_count,
          pointers_skipped=skipped_count,
          tokens_used=final_tokens,
          warnings=warnings
      )
  ```

**⚠️ FLASH WARNING:**
- Emergency brake na 90% budget (ne čekaj 100%)
- Log warning ako premaši budget
- Ne crashuj - return partial result

***

### Task 7.2.7: Add Unit Tests for Pointer Resolver
**CILJ:** Test pointer resolution logic

- [ ] **Create test file:** `tests/test_pointer_resolver.py`
- [ ] **Test selective fetch within budget:**
  ```python
  def test_selective_fetch_within_budget():
      # Mock client that returns small content
      mock_client = Mock()
      mock_client.fetch_exact.return_value = FetchExactResponse(
          content="Small content",
          lines_read=1,
          file_path="test.md",
          error=None
      )
      
      pointers = [
          Pointer(file_path="test.md", section="Test", line_range=(0, 1), keywords=[], confidence=0.9),
          Pointer(file_path="test2.md", section="Test2", line_range=(0, 1), keywords=[], confidence=0.8),
      ]
      
      resolver = PointerResolver(mock_client, budget=1000)
      result = resolver.resolve(pointers, fetch_strategy="selective")
      
      # Should fetch both (small content fits in budget)
      assert result.pointers_fetched == 2
      assert result.pointers_skipped == 0
      assert result.tokens_used < 1000
  ```

- [ ] **Test selective fetch exceeds budget:**
  ```python
  def test_selective_fetch_exceeds_budget():
      # Mock client that returns huge content
      mock_client = Mock()
      mock_client.fetch_exact.return_value = FetchExactResponse(
          content="X" * 10000,  # Huge content
          lines_read=100,
          file_path="huge.md",
          error=None
      )
      
      pointers = [
          Pointer(file_path="huge.md", section="Test", line_range=(0, 100), keywords=[], confidence=0.9),
          Pointer(file_path="huge2.md", section="Test2", line_range=(0, 100), keywords=[], confidence=0.8),
      ]
      
      resolver = PointerResolver(mock_client, budget=500)  # Small budget
      result = resolver.resolve(pointers, fetch_strategy="selective")
      
      # Should fetch first, skip second (budget exhausted)
      assert result.pointers_fetched == 1
      assert result.pointers_skipped == 1
  ```

- [ ] **Test metadata-only strategy:**
  ```python
  def test_metadata_only_strategy():
      mock_client = Mock()
      
      pointers = [Pointer(file_path="test.md", section="Test", line_range=(0, 10), keywords=["test"], confidence=0.9)]
      
      resolver = PointerResolver(mock_client, budget=1000)
      result = resolver.resolve(pointers, fetch_strategy="none")
      
      # Should not call fetch_exact
      mock_client.fetch_exact.assert_not_called()
      
      # Should return metadata
      assert result.pointers_fetched == 0
      assert result.pointers_skipped == 1
      assert "test.md" in result.context
  ```

- [ ] **Test fetch failure handling:**
  ```python
  def test_fetch_failure_handling():
      # Mock client that fails to fetch
      mock_client = Mock()
      mock_client.fetch_exact.return_value = None  # Fetch failed
      
      pointers = [Pointer(file_path="missing.md", section="Test", line_range=(0, 10), keywords=[], confidence=0.9)]
      
      resolver = PointerResolver(mock_client, budget=1000)
      result = resolver.resolve(pointers, fetch_strategy="selective")
      
      # Should handle gracefully
      assert result.pointers_fetched == 0
      assert result.pointers_skipped == 1
      assert len(result.warnings) > 0
  ```

**⚠️ FLASH WARNING:**
- Test sa realisticnim token sizes (mali i veliki content)
- Test edge case: budget=0, prazan pointers list, sve fetch-ovi fail
- Mock `fetch_exact` - ne zovi pravi API u unit testovima

***

## FAZA 7.3: PROMPT ENGINEERING

### Task 7.3.1: Locate System Prompt
**CILJ:** Pronađi gdje je system prompt u Antigravity kodu

- [ ] **Search for prompt files:**
  ```bash
  find ./antigravity -name "*prompt*" -o -name "*system*"
  grep -r "system.*prompt" ./antigravity
  grep -r "You are" ./antigravity  # Common prompt pattern
  ```

- [ ] **Document findings:**
  - File path: `_______________`
  - Format: (Plain text / JSON / YAML / Code string)
  - How loaded: (File read / Hardcoded / Environment var)
  - Current content summary: `_______________`

- [ ] **Create backup:**
  ```bash
  cp [prompt_file] [prompt_file].backup_20260211
  ```

**⚠️ FLASH WARNING:**
- NE modifikuj prompt dok ne napraviš backup
- Ako ne možeš naći prompt, ZAUSTAVI SE i pitaj

***

### Task 7.3.2: Add Pointer Understanding Section
**CILJ:** Nauči LLM da radi sa pointerima

- [ ] **Append to system prompt:**
  ```markdown
  ---
  
  ## Working with Search Results (Pointers)
  
  When answering questions, you may receive search results in two formats:
  
  ### 1. Full Content (Fetched)
  Prefixed with 📄, includes complete text:
  ```
  ## 📄 development_log.md (Lines 145-160)
  **Section:** Release v0.2.62
  **Confidence:** 0.85
  
  [full content here...]
  ```
  
  → Use this content directly to answer.
  
  ### 2. Pointer References (Not Fetched)
  Prefixed with 📍, includes only metadata:
  ```
  ## 📍 Additional Relevant Locations
  
  1. **config.json** (Lines 20-30) - Section: "Database"
     Keywords: supabase, connection, api_key
     Confidence: 0.75
  ```
  
  → This tells you WHERE information exists, but you don't have the content yet.
  
  ## Decision Guidelines
  
  When you see pointer references:
  
  1. **Can you answer from metadata alone?**
     - If keywords + filename give enough context → Answer directly
     - Example: User asks "Do we use Supabase?" → Pointer shows config.json with keyword "supabase" → Answer: "Yes"
  
  2. **Do you need exact details?**
     - If metadata insufficient → Tell user: "I found relevant info in [file], but need to fetch details. Should I?"
     - WAIT for user confirmation before requesting fetch
  
  3. **Multiple pointers match?**
     - List them and ask user: "I found info in 3 locations: [A, B, C]. Which would you like me to explore?"
  
  ## What NOT to Do
  
  ❌ Don't automatically fetch all pointers (wastes tokens)
  ❌ Don't say "I don't know" if pointers exist (you know WHERE to look)
  ❌ Don't confuse pointer metadata with actual content
  
  ## Example Interaction
  
  User: "What's in the releases bucket?"
  
  System provides:
  ```
  📍 development_log.md (Section: "v0.2.62", Keywords: releases, bucket, storage)
  ```
  
  ✅ Good response:
  "Based on the development log (v0.2.62 section), there's information about a 'releases' bucket for storage. Would you like me to fetch the exact details?"
  
  ❌ Bad response:
  "I don't have information about that." (You DO - it's in the pointer!)
  ```

**⚠️ FLASH WARNING:**
- Dodaj na KRAJ prompt-a (ne mijenjaj postojeći dio)
- Koristi markdown formatting (bolje čitljivost)
- Examples su KRITIČNI - LLM uči po primjerima

***

### Task 7.3.3: Add Fetch Request Instructions
**CILJ:** Nauči LLM kako zatražiti fetch

- [ ] **Append to system prompt:**
  ```markdown
  ---
  
  ## Requesting Content Fetch (Advanced)
  
  If you determine that full content is needed, you can request it using this format:
  
  ```
  [FETCH_REQUEST]
  File: development_log.md
  Lines: 145-160
  Reason: User asked for specific release details
  [/FETCH_REQUEST]
  ```
  
  The system will then fetch the content and provide it in the next turn.
  
  **When to fetch:**
  - User explicitly asks for "exact details", "full text", "complete information"
  - Pointer keywords match but you need specifics (dates, numbers, exact wording)
  - User's question can't be answered from metadata alone
  
  **When NOT to fetch:**
  - General questions answerable from keywords
  - User is exploring/browsing (offer options instead)
  - Multiple pointers match (ask user to choose first)
  ```

**NAPOMENA:** Ovo je OPCIONO ako želiš da LLM može eksplicitno zatražiti fetch. Alternativa je da Antigravity automatski odluči.

**⚠️ FLASH WARNING:**
- Ovaj dio je optional - odluči da li ti treba
- Ako implementiraš, morat ćeš parsirati `[FETCH_REQUEST]` u Antigravity kodu

***

### Task 7.3.4: Update Prompt with Croatian Language Support
**CILJ:** Jer tvoj user priča hrvatski

- [ ] **Add language section:**
  ```markdown
  ---
  
  ## Language: Croatian (Hrvatski)
  
  User may ask questions in Croatian. When responding:
  
  - Pointer metadata (file paths, keywords) will be in mixed English/Croatian
  - Respect user's language choice (if they ask in Croatian, respond in Croatian)
  - Technical terms (file paths, code) stay in English
  - Explanations adapt to user's language
  
  Example:
  User: "Što je u releases bucketu?"
  Response: "Na osnovu development loga (sekcija v0.2.62), postoji 'releases' bucket za storage. Želiš li da dohvatim točne detalje?"
  ```

**⚠️ FLASH WARNING:**
- Ako LLM nije dobar sa hrvatskim, možda je bolje držat sve na engleskom
- Testiraj sa real upitima prije production

***

### Task 7.3.5: Test Prompt with Real Scenarios
**CILJ:** Verifikuj da prompt radi

- [ ] **Create test scenarios file:** `tests/prompts/pointer_scenarios.txt`
- [ ] **Test Scenario 1: Metadata sufficient**
  ```
  System provides:
  📍 config.json (Keywords: supabase, api_key, connection)
  
  User asks: "Do we use Supabase?"
  
  Expected: "Yes, based on config.json which contains Supabase configuration (API key and connection settings)."
  
  NOT expected: "I need to fetch the file first." (metadata alone is sufficient)
  ```

- [ ] **Test Scenario 2: Need exact details**
  ```
  System provides:
  📍 development_log.md (Section: "v0.2.62", Keywords: releases, bucket, added)
  
  User asks: "When was the releases bucket added?"
  
  Expected: "I found information about the releases bucket in development_log.md (v0.2.62 section). Should I fetch the exact details about when it was added?"
  
  NOT expected: "In v0.2.62" (don't guess from metadata)
  ```

- [ ] **Test Scenario 3: Multiple pointers**
  ```
  System provides:
  📍 1. README.md (Keywords: supabase, setup)
  📍 2. config.json (Keywords: supabase, credentials)
  📍 3. development_log.md (Keywords: supabase, migration)
  
  User asks: "Tell me about Supabase setup"
  
  Expected: "I found Supabase information in 3 places:
  1. README.md - likely setup instructions
  2. config.json - configuration/credentials
  3. development_log.md - migration notes
  Which would you like me to check first?"
  
  NOT expected: Fetch all 3 automatically
  ```

- [ ] **Manual testing:**
  - Start Antigravity with updated prompt
  - Run each scenario
  - Document actual responses
  - Iterate prompt if responses don't match expected

**⚠️ FLASH WARNING:**
- NE assume da prompt radi - TEST sa realnim queryjem
- Ako LLM ignoriše upute, možda ih treba reformulirat ili podebljat

***

## FAZA 7.4: END-TO-END INTEGRATION

### Task 7.4.1: Integrate KronosClient into Antigravity
**CILJ:** Wire up client u Antigravity main flow

- [ ] **Find Antigravity main handler:**
  - Locate gdje se handla user input
  - Tipično: `handle_message()`, `process_query()`, `chat()`
  
- [ ] **Initialize KronosClient:**
  ```python
  # U Antigravity initialization code (npr. __init__ ili setup funkcija)
  
  from antigravity.clients.kronos_client import KronosClient
  from antigravity.services.pointer_resolver import PointerResolver
  
  class Antigravity:
      def __init__(self, ...):
          # ... existing initialization
          
          # Initialize Kronos client
          self.kronos_client = KronosClient(
              base_url="http://localhost:8000",  # TODO: Move to config
              timeout=30,
              max_retries=3
          )
          
          # Initialize pointer resolver
          self.pointer_resolver = PointerResolver(
              kronos_client=self.kronos_client,
              budget=4000,  # TODO: Adjust based on LLM context window
              pointer_metadata_tokens=100
          )
          
          logger.info("Kronos integration initialized")
  ```

**⚠️ FLASH WARNING:**
- base_url treba biti u config file-u, ne hardcoded
- budget zavisi od koji LLM koristi (GPT-4: 8k, Gemini: 32k, Claude: 100k)

***

### Task 7.4.2: Integrate Query Flow
**CILJ:** Pozovi Kronos u Antigravity message handler-u

- [ ] **Modify message handler:**
  ```python
  async def handle_message(self, user_message: str) -> str:
      """
      Handle user message with Kronos integration.
      
      Flow:
      1. Query Kronos for relevant information
      2. Resolve pointers into context
      3. Build LLM prompt with context
      4. Get LLM response
      5. Return to user
      """
      
      logger.info(f"User message: {user_message[:100]}...")
      
      # STEP 1: Query Kronos
      kronos_response = self.kronos_client.query(
          text=user_message,
          limit=4000,
          silent=True
      )
      
      # STEP 2: Check if Kronos is available
      if kronos_response is None:
          logger.warning("Kronos unavailable, proceeding without context")
          # Fallback: Answer without Kronos context
          return await self._answer_without_context(user_message)
      
      # STEP 3: Resolve pointers
      context_result = self.pointer_resolver.resolve(
          pointers=kronos_response.pointers,
          fetch_strategy="selective"  # Smart fetching
      )
      
      # STEP 4: Build prompt with context
      full_prompt = self._build_prompt_with_context(
          user_message=user_message,
          context=context_result.context,
          query_response=kronos_response
      )
      
      # STEP 5: Get LLM response
      llm_response = await self.llm.generate(full_prompt)
      
      # STEP 6: Log metrics
      logger.info(
          f"Response generated: "
          f"pointers={context_result.pointers_fetched}/{len(kronos_response.pointers)}, "
          f"tokens={context_result.tokens_used}"
      )
      
      return llm_response
  ```

**⚠️ FLASH WARNING:**
- `async/await` ako Antigravity je async, inače makni `async`
- Fallback kada Kronos ne radi je OBAVEZAN
- Log metrics za svaki request (debugging!)

***

### Task 7.4.3: Implement Prompt Builder
**CILJ:** Kombiniraj system prompt + context + user query

- [ ] **Implement _build_prompt_with_context():**
  ```python
  def _build_prompt_with_context(
      self,
      user_message: str,
      context: str,
      query_response: QueryResponse
  ) -> str:
      """
      Build LLM prompt combining:
      - System prompt (instructions)
      - Kronos context (search results)
      - User message (query)
      
      DEFENSIVE: Handles empty context gracefully
      """
      
      # Load system prompt
      system_prompt = self._load_system_prompt()
      
      # Build context section
      if context and len(context.strip()) > 0:
          context_section = f"""
  ## Relevant Information from Knowledge Base
  
  {context}
  
  ---
  """
      else:
          context_section = ""
      
      # Build full prompt
      full_prompt = f"""{system_prompt}
  
  {context_section}
  
  ## User Question
  
  {user_message}
  
  ## Your Response
  
  """
      
      return full_prompt
  ```

**⚠️ FLASH WARNING:**
- Format zavisi od koji LLM koristi (OpenAI ima messages format, drugi imaju single string)
- Prilagodi format prema svom LLM-u

***

### Task 7.4.4: Implement Fallback Without Context
**CILJ:** Graceful degradation kada Kronos ne radi

- [ ] **Implement _answer_without_context():**
  ```python
  async def _answer_without_context(self, user_message: str) -> str:
      """
      Answer user query without Kronos context.
      
      Use when:
      - Kronos is down
      - Kronos returns no results
      - Network error
      
      DEFENSIVE: Always provides an answer
      """
      
      logger.warning("Answering without Kronos context")
      
      # Build prompt without context
      system_prompt = self._load_system_prompt()
      
      fallback_prompt = f"""{system_prompt}
  
  ⚠️ Note: Knowledge base search is currently unavailable.
  
  ## User Question
  
  {user_message}
  
  ## Your Response
  
  """
      
      response = await self.llm.generate(fallback_prompt)
      
      # Prepend disclaimer
      return f"⚠️ *Note: Knowledge base unavailable, answering from general knowledge only.*\n\n{response}"
  ```

**⚠️ FLASH WARNING:**
- User MORA znati da odgovor nije iz knowledge base
- Disclaimer je obavezan

***

### Task 7.4.5: Add Session Management
**CILJ:** Track session across multiple queries

- [ ] **Add session tracking:**
  ```python
  import uuid
  from datetime import datetime
  
  class Antigravity:
      def __init__(self, ...):
          # ... existing code
          
          # Session management
          self.session_id = self._generate_session_id()
          self.session_start = datetime.now()
          self.query_count = 0
          
          # Pass session_id to Kronos client
          self.kronos_client = KronosClient(
              base_url=...,
              session_id=self.session_id
          )
      
      def _generate_session_id(self) -> str:
          """Generate unique session identifier"""
          timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
          unique_id = uuid.uuid4().hex[:8]
          return f"antigravity_{timestamp}_{unique_id}"
      
      async def handle_message(self, user_message: str) -> str:
          self.query_count += 1
          logger.info(f"[Session {self.session_id}] Query #{self.query_count}")
          
          # ... rest of handler
  ```

**⚠️ FLASH WARNING:**
- Session ID mora biti unique per conversation
- Track query count za debugging
- Session ID se šalje u sve Kronos API pozive (za circular request detection)

***

### Task 7.4.6: Add Error Handling Wrapper
**CILJ:** Catch all errors, never crash

- [ ] **Wrap handler u try-except:**
  ```python
  async def handle_message(self, user_message: str) -> str:
      try:
          # ... main logic (from Task 7.4.2)
          
      except Exception as e:
          logger.error(f"Unexpected error in handle_message: {e}", exc_info=True)
          
          # Return user-friendly error
          return (
              "I encountered an error while processing your request. "
              f"Error details: {str(e)}\n\n"
              "Please try rephrasing your question or contact support if the issue persists."
          )
  ```

**⚠️ FLASH WARNING:**
- NIKAD ne pusti exception do user-a
- Log full traceback (`exc_info=True`)
- User-friendly error message

***

## FAZA 7.5: TESTING & VALIDATION

### Task 7.5.1: End-to-End Integration Test
**CILJ:** Test cijeli flow Antigravity → Kronos → Response

- [ ] **Create test file:** `tests/integration/test_antigravity_kronos.py`
- [ ] **Setup test environment:**
  ```python
  import pytest
  from antigravity import Antigravity
  
  @pytest.fixture
  def antigravity_instance():
      """Create Antigravity instance with test configuration"""
      ag = Antigravity(
          kronos_url="http://localhost:8000",
          llm_model="test",  # Mock LLM
          config_path="tests/fixtures/test_config.yml"
      )
      yield ag
      ag.shutdown()  # Cleanup
  ```

- [ ] **Test happy path:**
  ```python
  @pytest.mark.asyncio
  async def test_query_with_pointers(antigravity_instance):
      """Test query that returns pointers and gets resolved"""
      
      # This requires Kronos to be running!
      response = await antigravity_instance.handle_message(
          "What is in the releases bucket?"
      )
      
      # Assert response is not empty
      assert response
      assert len(response) > 0
      
      # Assert no error messages
      assert "error" not in response.lower()
      assert "unavailable" not in response.lower()
  ```

- [ ] **Test Kronos down scenario:**
  ```python
  @pytest.mark.asyncio
  async def test_query_kronos_down(antigravity_instance):
      """Test graceful degradation when Kronos is unavailable"""
      
      # Stop Kronos or change URL to invalid
      antigravity_instance.kronos_client.base_url = "http://localhost:9999"  # Invalid port
      
      response = await antigravity_instance.handle_message(
          "Test query"
      )
      
      # Should still return response (fallback mode)
      assert response
      
      # Should include disclaimer
      assert "unavailable" in response.lower() or "warning" in response.lower()
  ```

**⚠️ FLASH WARNING:**
- Integration testovi trebaju running Kronos server
- Mark sa `@pytest.mark.integration` da se mogu skip-ati
- Dodaj u CI/CD tylko ako imaš test environment

***

### Task 7.5.2: Manual Testing Checklist
**CILJ:** Ručno testiraj sve scenarije

- [ ] **Scenario 1: Simple factual query**
  - User input: "What is Supabase?"
  - Expected: Answer from indexed documents ili "found in [file]"
  - Actual result: `_______________`

- [ ] **Scenario 2: Query requiring exact details**
  - User input: "When was v0.2.62 released?"
  - Expected: Model fetches exact section, provides specific answer
  - Actual result: `_______________`

- [ ] **Scenario 3: Query with no results**
  - User input: "Tell me about quantum physics"
  - Expected: "No relevant information in knowledge base" ili general knowledge answer
  - Actual result: `_______________`

- [ ] **Scenario 4: Multiple relevant results**
  - User input: "How do I configure the database?"
  - Expected: Model shows multiple locations, asks user to choose
  - Actual result: `_______________`

- [ ] **Scenario 5: Croatian query**
  - User input: "Što je u releases bucketu?"
  - Expected: Answer in Croatian
  - Actual result: `_______________`

- [ ] **Scenario 6: Follow-up question**
  - First: "Tell me about releases"
  - Then: "When was it added?"
  - Expected: Model understands context, fetches relevant info
  - Actual result: `_______________`

**⚠️ FLASH WARNING:**
- Dokumentiraj SVE rezultate
- Ako bilo koji scenario faila, debug prije nego nastaviš

***

### Task 7.5.3: Performance Benchmarking
**CILJ:** Measure end-to-end latency

- [ ] **Create benchmark script:** `scripts/benchmark_integration.py`
- [ ] **Measure components:**
  ```python
  import time
  import statistics
  
  async def benchmark_query(antigravity, query: str, iterations: int = 10):
      """Benchmark single query multiple times"""
      
      timings = {
          'kronos_query': [],
          'pointer_resolution': [],
          'llm_generation': [],
          'total': []
      }
      
      for i in range(iterations):
          start = time.time()
          
          # Time Kronos query
          t0 = time.time()
          kronos_response = antigravity.kronos_client.query(query)
          timings['kronos_query'].append(time.time() - t0)
          
          # Time pointer resolution
          t1 = time.time()
          context_result = antigravity.pointer_resolver.resolve(kronos_response.pointers)
          timings['pointer_resolution'].append(time.time() - t1)
          
          # Time LLM (approximate - depends on your implementation)
          t2 = time.time()
          response = await antigravity.handle_message(query)
          timings['llm_generation'].append(time.time() - t2)
          
          # Total
          timings['total'].append(time.time() - start)
      
      # Print statistics
      for component, times in timings.items():
          avg = statistics.mean(times)
          median = statistics.median(times)
          print(f"{component}:")
          print(f"  Avg: {avg:.3f}s")
          print(f"  Median: {median:.3f}s")
          print(f"  Min: {min(times):.3f}s")
          print(f"  Max: {max(times):.3f}s")
  ```

- [ ] **Run benchmarks:**
  - Simple query (expected <2s total)
  - Complex query with multiple pointers (expected <5s)
  - Query requiring fetch (expected <3s)

- [ ] **Document results:** `docs/PERFORMANCE.md`

**⚠️ FLASH WARNING:**
- Benchmark na real hardware (ne development laptop)
- Run multiple iterations (min 10) za avg
- Identify bottlenecks (koji component je najsporiji?)

***

## COMPLETION CHECKLIST - FAZA 7

- [ ] ✅ Task 7.0.x: Architecture documented
- [ ] ✅ Task 7.1.x: KronosClient implemented and tested
- [ ] ✅ Task 7.2.x: PointerResolver implemented and tested
- [ ] ✅ Task 7.3.x: System prompt updated
- [ ] ✅ Task 7.4.x: Antigravity integration complete
- [ ] ✅ Task 7.5.x: Testing complete, all scenarios pass
- [ ] ✅ Manual testing checklist 100% complete
- [ ] ✅ Performance benchmarks documented
- [ ] ✅ No errors in logs during testing
- [ ] ✅ Graceful degradation verified (Kronos down scenario)
- [ ] ✅ Croatian language support verified
- [ ] ✅ Code reviewed and committed

***

**Total Estimated Time for Faza 7: 2-3 dana**

**KRITIČNI ZAHTJEVI ZA FLASH:**
1. TESTIRAJ SVAKI TASK prije nego ideš na sljedeći
2. NE PRETPOSTAVLJAJ - ako nešto nije jasno, PITAJ
3. LOG SVE - svaki error, svaki decision, svaku metriku
4. DEFENSIVE PROGRAMMING - nikad ne crashuj, uvijek return nešto
5. BACKWARD COMPATIBILITY - stari kod mora raditi dok ne migriraš sve
 🚀