param (
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [int]$Limit = 5
)

$Url = "http://127.0.0.1:8000/query"

# Provjeri je li server aktivan
try {
    $Test = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
}
catch {
    Write-Host "❌ Greška: Kronos server nije pokrenut!" -ForegroundColor Red
    Write-Host "Pokreni ga u drugom terminalu naredbom: .\run.ps1 serve" -ForegroundColor Yellow
    exit 1
}

$Body = @{
    text  = $Query
    limit = $Limit
} | ConvertTo-Json

Write-Host "🔍 Šaljem upit serveru: '$Query'..." -ForegroundColor Cyan

try {
    $Response = Invoke-RestMethod -Uri $Url -Method Post -Body $Body -ContentType "application/json"
    
    if ($Response.results.Count -eq 0) {
        Write-Host "Nema rezultata." -ForegroundColor Gray
    }
    else {
        foreach ($res in $Response.results) {
            Write-Host "`n--- Citat #$($res.id or 'N/A') ---" -ForegroundColor Green
            Write-Host "Izvor: $($res.metadata.source)" -ForegroundColor Gray
            Write-Host $res.content
            Write-Host ("-" * 50) -ForegroundColor DarkGray
        }
    }
}
catch {
    Write-Host "❌ Greška pri komunikaciji sa serverom." -ForegroundColor Red
    Write-Host $_.Exception.Message
}
