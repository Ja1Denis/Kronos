# PicardAi - Kronos SSE Konekcija: Poznati Problem i Rješenje

## Problem

Nakon restarta Windows računala, PicardAi Docker kontejner ne može pristupiti Kronos MCP serveru.

**Simptomi:**
- Picard javlja grešku `-32602` ili `Connection refused`
- `host.docker.internal:8765` je nedostupan
- Port 8765 nije aktivan (potvrđeno s `netstat`)

## Uzrok

`start_kronos.ps1` skripta **ne uspijeva** pokrenuti SSE server zbog encoding greške:

```
The string is missing the terminator: "
At E:\G\GeminiCLI\ai-test-project\kronos\start_kronos.ps1:53 char:23
Missing closing '}' in statement block
```

Skripta sadrži hrvatska slova i Unicode znakove (`Čistim`, `✅`) koji pucaju
kada se `start_kronos.ps1` poziva ugnježdeno (npr. iz `Start-Process -Command`).

**Važno:** `kronos_ping` via MCP BridGE (stdio) radi jer VS Code IDE pokreće
Kronos odvojeno. Ali SSE server na portu 8765 (kojeg Picard treba) **nije pokrenut**.

## Rješenje

Umjesto `start_kronos.ps1`, koristiti `run_sse.ps1` koji **nema problematičnih znakova**:

```powershell
# Lokacija: e:\G\GeminiCLI\ai-test-project\kronos\run_sse.ps1
$env:PYTHONPATH = $PSScriptRoot
$env:KRONOS_PORT = "8765"
Set-Location $PSScriptRoot
python -m src.mcp_server --sse --port 8765
```

**Pokretanje:**
```powershell
# U VS Code terminalu ili PowerShell:
cd e:\G\GeminiCLI\ai-test-project\kronos
.\run_sse.ps1
```

## Verifikacija

```powershell
# Provjera da port sluša:
netstat -ano | findstr ":8765"
# Očekivani output: TCP 0.0.0.0:8765 LISTENING
```

## Datum otkrića

2026-02-21 — Antigravity + Denis debug sesija

## Root Cause #2: MCP Handshake (KRITIČNO)

Čak i nakon pokretanja SSE servera, PicardAi je i dalje dobivao `-32602`.

**Uzrok:** MCP protokol zahtijeva **handshake sekvenciju** prije `tools/call`:
1. `initialize` → server odgovori s capabilities
2. `notifications/initialized` → klijent potvrdi
3. **Tek tada** `tools/call` → radi!

PicardAi je **preskakao korake 1-2** i odmah slao `tools/call`, pa je FastMCP SSE handler odbijao sa `-32602 Invalid request parameters`.

**Fix:** Implementiran puni MCP handshake u `KronosClient._call_tool()` metodi u `entrypoint.py`.

## Zahvaćeni Komponente

- `PicardAi` Docker kontejner (koristi `host.docker.internal:8765`)
- `kronos/start_kronos.ps1` (problematična skripta)
- `kronos/run_sse.ps1` (rješenje - nova čista skripta)

## Preporuka

Postaviti `run_sse.ps1` kao Task u VS Code (`tasks.json`) ili kao Windows autostart
kako bi se SSE server automatski pokretao s računalom.
