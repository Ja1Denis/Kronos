param (
    [string]$Command,
    [string]$Path,
    [switch]$Recursive,
    [string]$Text,
    [int]$Limit = 5
)

# Aktiviraj venv
$VenvPath = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Venv nije pronadjen! Pokreni setup.ps1." -ForegroundColor Red
    exit 1
}
. $VenvPath

# Pokreni Python
if ($Command -eq "ingest") {
    $Params = @("ingest", "$Path")
    if ($Recursive) { $Params += "--recursive" }
    python src/main.py @Params
}
elseif ($Command -eq "query") {
    python src/main.py query "$Text" --limit $Limit
}
elseif ($Command -eq "check_db") {
    python check_db.py
}
else {
    python src/main.py --help
}
