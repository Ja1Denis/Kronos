param (
    [string]$Command = "stats",
    [string]$Param1 = ".",
    [int]$Limit = 5,
    [string]$Project = "",
    [switch]$Recursive
)

# Aktiviraj venv
$VenvPath = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Venv nije pronadjen! Pokreni setup.ps1." -ForegroundColor Red
    exit 1
}
. $VenvPath

# Postavi PYTHONPATH na trenutni direktorij kako bi 'src' importi radili
$env:PYTHONPATH = "$PWD"

# Pokreni Python alat Kronos
if ($Command -eq "ingest") {
    $KronosArgs = @("ingest", "$Param1")
    if ($Recursive) { $KronosArgs += "--recursive" }
    python src/main.py @KronosArgs
}
elseif ($Command -eq "ask") {
    if ($Project) {
        python src/main.py ask "$Param1" --limit $Limit --project "$Project"
    }
    else {
        python src/main.py ask "$Param1" --limit $Limit
    }
}
elseif ($Command -eq "watch") {
    python src/main.py watch "$Param1"
}
elseif ($Command -eq "chat") {
    python src/main.py chat
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
