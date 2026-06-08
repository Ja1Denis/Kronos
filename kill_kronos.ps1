# kill_kronos.ps1 — Čisti Kronos server + MCP bridge procese
# ============================================================
# Korištenje:
#   .\kill_kronos.ps1              # Čisti port 8765 (default)
#   .\kill_kronos.ps1 -Port 9000   # Custom port
# ============================================================

param(
    [int]$Port = 8765
)

Write-Host "`n🔍 Tražim procese na portu $Port..." -ForegroundColor Yellow

# 1. Clear server port
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $processes) {
        try {
            Write-Host "  ❌ Gasim server proces $p na portu $Port" -ForegroundColor Red
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "  ⚠️ Nije moguće zaustaviti proces $p" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Seconds 1
    Write-Host "  ✅ Port $Port je slobodan." -ForegroundColor Green
}
else {
    Write-Host "  ✅ Port $Port je već slobodan." -ForegroundColor Green
}

# 2. Kill stale mcp_bridge.py processes
# Ovi procesi drže mrtve SSE konekcije nakon restarta servera.
# IDE ih automatski obnovi kad ih ugasimo.
Write-Host "`n🔍 Tražim mcp_bridge.py procese..." -ForegroundColor Yellow
$bridgeProcesses = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match "mcp_bridge\.py" }
if ($bridgeProcesses) {
    Write-Host "  ❌ Gasim $($bridgeProcesses.Count) bridge proces(a)..." -ForegroundColor Red
    $bridgeProcesses | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    Write-Host "  ✅ Bridge procesi očišćeni — IDE će ih automatski obnoviti." -ForegroundColor Green
}
else {
    Write-Host "  ✅ Nema aktivnih bridge procesa." -ForegroundColor Green
}

Write-Host "`n🚀 Kronos je spreman za svjež start. Pokrenite: .\start_kronos.ps1" -ForegroundColor Cyan
Write-Host ""
