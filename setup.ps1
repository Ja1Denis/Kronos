Write-Host "Inicijalizacija okruženja za Projekt Kronos..." -ForegroundColor Cyan

# 1. Provjeri Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "GRESKA: Python nije pronadjen! Molim instaliraj Python 3.10+." -ForegroundColor Red
    exit 1
}

# 2. Kreiraj venv ako ne postoji
if (-not (Test-Path "venv")) {
    Write-Host "Kreiram virtualno okruženje (venv)..." -ForegroundColor Yellow
    python -m venv venv
}
else {
    Write-Host "venv vec postoji." -ForegroundColor Gray
}

# 3. Aktiviraj venv i instaliraj zahtjeve
Write-Host "Pokrecem instalaciju biblioteka..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "GRESKA: Nije moguce aktivirati venv." -ForegroundColor Red
    exit 1
}

pip install -r requirements.txt

# 4. Konfiguracija
Write-Host "Pokrecem konfiguraciju..." -ForegroundColor Yellow
python configure.py

Write-Host "Sve gotovo! Okruženje je spremno." -ForegroundColor Green
Write-Host "Za aktivaciju tipkaj: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
