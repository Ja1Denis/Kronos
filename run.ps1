param (
    [string]$Command,
    [string]$Param1,
    [switch]$Recursive,
    [int]$Limit = 5
)

# Aktiviraj venv
$VenvPath = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Venv nije pronadjen! Pokreni setup.ps1." -ForegroundColor Red
    exit 1
}
. $VenvPath

# Pokreni Python alat Kronos
if ($Command -eq "ingest") {
    $KronosArgs = @("ingest", "$Param1")
    if ($Recursive) { $KronosArgs += "--recursive" }
    python src/main.py @KronosArgs
}
elseif ($Command -eq "ask") {
    python src/main.py ask "$Param1" --limit $Limit
}
elseif ($Command -eq "watch") {
    python src/main.py watch "$Param1"
}
elseif ($Command -eq "stats") {
    python src/main.py stats
}
elseif ($Command -eq "serve") {
    python src/server.py
}
elseif ($Command -eq "wipe") {
    python src/main.py wipe
}
else {
    # Ako nema komande, pokaži help
    python src/main.py --help
}
