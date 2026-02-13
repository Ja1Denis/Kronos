# kill_kronos.ps1
Write-Host "Searching for processes on port 8000..." -ForegroundColor Yellow

# 1. Clear port 8000
$port = 8000
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $processes) {
        try {
            Write-Host "Killing process $p on port $port" -ForegroundColor Red
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "Warning: Could not stop process $p" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Seconds 1
    Write-Host "Port $port is clear." -ForegroundColor Green
}
else {
    Write-Host "Port $port is already clear." -ForegroundColor Green
}

# 2. Kill remaining Python processes associated with kronos
Write-Host "Cleaning up Python processes..." -ForegroundColor Yellow
$pyProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pyProcs) {
    foreach ($proc in $pyProcs) {
        try {
            $path = $proc.Path
            if ($path -like "*kronos*") {
                Write-Host "Killing Python process: $($proc.Id)" -ForegroundColor Red
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            # Path might not be accessible
        }
    }
}

Write-Host "Kronos is ready for a fresh start." -ForegroundColor Cyan
