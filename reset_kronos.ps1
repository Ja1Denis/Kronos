# Cleanup and Reset Kronos Environment
Write-Host "===============================================" -ForegroundColor Magenta
Write-Host "🧹 KRONOS RESET: Čišćenje i ponovno pokretanje" -ForegroundColor Magenta
Write-Host "===============================================" -ForegroundColor Magenta

# 1. Kill processes specifically by Port 8000 (Kronos Server)
Write-Host "1/3 Oslobađanje porta 8000..." -ForegroundColor Cyan
$portProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue
if ($portProcess) {
    foreach ($p in $portProcess) {
        Write-Host "   -> Ubijam proces ID: $p" -ForegroundColor Yellow
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
}

# 2. Kill any remaining uvicorn/python instances started from this directory
Write-Host "2/3 Čišćenje preostalih kronos procesa..." -ForegroundColor Cyan
Get-Process python, uvicorn -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*kronos*" } | Stop-Process -Force

# 3. Clean Python Cache (prevents old code execution)
Write-Host "3/3 Čišćenje cache-a (__pycache__)..." -ForegroundColor Cyan
Get-ChildItem -Path . -Filter "__pycache__" -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

Write-Host "✅ Sustav je čist." -ForegroundColor Green

# 4. Start Server
Write-Host "`n🚀 Pokretanje servera..." -ForegroundColor Cyan
powershell -File .\start_kronos.ps1

Write-Host "`n✨ SVE JE SPREMNO!" -ForegroundColor Magenta
Write-Host "===============================================" -ForegroundColor Magenta
