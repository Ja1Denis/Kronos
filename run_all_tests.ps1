# run_all_tests.ps1
Write-Host "🧪 Starting Kronos Full System Validation Suite..." -ForegroundColor Cyan

# Osigurajmo da je PYTHONPATH postavljen
$env:PYTHONPATH = "."

# 1. Unit Tests
Write-Host "`n📦 [1/3] Running Unit Tests..." -ForegroundColor Yellow
pytest tests/test_librarian_fts.py tests/test_chromadb_health.py tests/test_rust_engine.py -v -s

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Unit tests failed! Stopping." -ForegroundColor Red
    exit 1
}

# 2. Integration Tests 
Write-Host "`n🔗 [2/3] Running Integration Tests (API)..." -ForegroundColor Yellow
pytest tests/test_integration.py -v -s

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Integration tests failed! Stopping." -ForegroundColor Red
    exit 1
}

# 3. Load Tests
Write-Host "`n⚡ [3/3] Running Performance Load Tests..." -ForegroundColor Yellow
pytest tests/test_load.py -v -s

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Load tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✨ ALL TESTS PASSED! SISTEM JE STABILAN. ✨" -ForegroundColor Green
