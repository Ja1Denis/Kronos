# start_kronos.ps1

Write-Host "🚀 Pokrećem Kronos sustav u pozadini..." -ForegroundColor Cyan

# 1. Pokreni server u novom prozoru (minimizirano)
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\run.ps1 serve" -WindowStyle Minimized

Write-Host "⏳ Učitavam AI modele (ovo traje ~15 sekundi samo prvi put)..." -ForegroundColor Yellow

# 2. Čekaj dok server ne postane 'Healthy'
$maxRetries = 30
$retryCount = 0
$serverReady = $false

while (-not $serverReady -and $retryCount -lt $maxRetries) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
        if ($health.status -eq "healthy") {
            $serverReady = $true
        }
    }
    catch {
        $retryCount++
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
    }
}

if ($serverReady) {
    Write-Host "`n✅ Kronos je SPREMAN!" -ForegroundColor Green
    Write-Host "Sada možeš koristiti: " -NoNewline
    Write-Host ".\ask_fast.ps1 -Query '...'" -ForegroundColor White -BackgroundColor DarkBlue
}
else {
    Write-Host "`n❌ Server se nije pokrenuo na vrijeme. Provjeri terminal za greške." -ForegroundColor Red
}
