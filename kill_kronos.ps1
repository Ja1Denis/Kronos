# kill_kronos.ps1
Write-Host "🔍 Pretražujem procese koji zauzimaju port 8000..." -ForegroundColor Yellow

# 1. Oslobodi port 8000
$port = 8000
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $processes) {
        try {
            Write-Host "🔫 Prekidam proces $p na portu $port" -ForegroundColor Red
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "⚠️ Ne mogu ugasiti proces $p" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Seconds 1
    Write-Host "✅ Port $port je oslobođen." -ForegroundColor Green
}
else {
    Write-Host "✅ Port $port je slobodan." -ForegroundColor Green
}

# 2. Ugasi preostale Python procese povezane s kronosom
Write-Host "🔍 Čistim preostale Python procese u kronos mapi..." -ForegroundColor Yellow
$pyProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pyProcs) {
    foreach ($proc in $pyProcs) {
        try {
            if ($proc.Path -like "*kronos*") {
                Write-Host "🔫 Prekidam Python proces: $($proc.Id)" -ForegroundColor Red
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            # Putanja možda nije dostupna za neke sistemske procese
        }
    }
}

Write-Host "🚀 Kronos je spreman za novo pokretanje." -ForegroundColor Cyan
