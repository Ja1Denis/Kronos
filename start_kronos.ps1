# ============================================================
# Kronos MCP Server - Multi-Agent Launcher
# ============================================================
# Pokreće Kronos u SSE (HTTP) modu na portu 8765.
# Svi IDE prozori (VS Code, Cursor, Claude Desktop) 
# se spajaju na isti server.
#
# Korištenje:
#   .\start_kronos.ps1              # Default port 8765
#   .\start_kronos.ps1 -Port 9000   # Custom port
# ============================================================

param(
    [int]$Port = 8765
)

$KronosRoot = $PSScriptRoot

Write-Host ""
Write-Host "  =====================================" -ForegroundColor Magenta
Write-Host "   Kronos MCP Server (Multi-Agent)" -ForegroundColor White
Write-Host "  =====================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Port:      $Port" -ForegroundColor Cyan
Write-Host "  Endpoint:  http://localhost:$Port/sse" -ForegroundColor Green
Write-Host "  Root:      $KronosRoot" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  MCP Config za IDE:" -ForegroundColor Yellow
Write-Host '  {' -ForegroundColor DarkGray
Write-Host '    "mcpServers": {' -ForegroundColor DarkGray
Write-Host '      "kronos": {' -ForegroundColor DarkGray
Write-Host "        `"url`": `"http://localhost:$Port/sse`"" -ForegroundColor Green
Write-Host '      }' -ForegroundColor DarkGray
Write-Host '    }' -ForegroundColor DarkGray
Write-Host '  }' -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Ctrl+C za zaustavljanje" -ForegroundColor DarkGray
Write-Host "  =====================================" -ForegroundColor Magenta
Write-Host ""

# Kill any existing Kronos on same port
$existingProcess = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcess) {
    Write-Host "  Zaustavljam prethodni proces na portu $Port..." -ForegroundColor Yellow
    $existingProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

# Set environment
$env:PYTHONPATH = $KronosRoot
$env:KRONOS_PORT = $Port

# Start server
Set-Location $KronosRoot
python -m src.mcp_server --sse --port $Port
