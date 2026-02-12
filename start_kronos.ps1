# start_kronos.ps1

Write-Host "🚀 Pokrećem Kronos sustav u pozadini..." -ForegroundColor Cyan

# 1. Pokreni server u novom prozoru (minimizirano)
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\run.ps1 serve" -WindowStyle Minimized

Write-Host "⏳ Učitavam AI modele (ovo traje ~15 sekundi samo prvi put)..." -ForegroundColor Yellow

# 2. Čekaj dok server ne postane 'Healthy'
$maxRetries = 60
$retryCount = 0
$serverReady = $false
$StartTime = [System.Diagnostics.Stopwatch]::StartNew()
$Spinner = @('|', '/', '-', '\')

while (-not $serverReady -and $retryCount -lt $maxRetries) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
        if ($health.status -eq "healthy") {
            $serverReady = $true
        }
    }
    catch {
        $Elapsed = [math]::Round($StartTime.Elapsed.TotalSeconds, 1)
        Write-Host -NoNewline "`r⏳ Učitavam AI modele... $($Spinner[$retryCount % 4]) [$($Elapsed)s] " -ForegroundColor Yellow
        $retryCount++
        Start-Sleep -Milliseconds 500
    }
}

if ($serverReady) {
    Write-Host "`n`n✅ Kronos je SPREMAN!" -ForegroundColor Green
    Write-Host "Sada možeš koristiti: " -NoNewline
    Write-Host ".\ask_fast.ps1 -Query '...'" -ForegroundColor White -BackgroundColor DarkBlue
}
else {
    Write-Host "`n`n❌ Server se nije pokrenuo na vrijeme. Provjeri terminal za greške." -ForegroundColor Red
}
