# Problem: Kronos MCP Server EOF Connection Closed (Crash)

## Simptomi
Prilikom korištenja Kronosa kao MCP alata unutar IDE-a (Gemini CLI / Antigravity), alat `kronos_ping` radi bez problema, no `kronos_query` ili `kronos_stats` trenutačno zatvaraju konekciju uz grešku:
`Encountered error in step execution: error executing cascade step: CORTEX_STEP_TYPE_MCP_TOOL: calling "tools/call": EOF`

## Uzrok
Problem nije u kodu samog Kronos servera niti u enkripciji/encoding-u (`cp1252` vs `UTF-8`), iako do toga može doći u `stdio` modu.
Pravi uzrok bio je **usmjeravanje klijenta na krivu konfiguraciju** u `.gemini/antigravity/mcp_config.json`.

IDE je imao postavljeno:
```json
"command": "python",
"args": ["e:\\G\\GeminiCLI\\ai-test-project\\kronos_remote_repo\\src\\mcp_server.py"]
```
Koristio je **globalni (sistemski) Python** umjesto onoga iz virtualnog okruženja (`venv`) specifičnog za Kronos projekt. Globalni Python obično **nema instalirane potrebne biblioteke** popur `chromadb`.
Također, putanja je pogrešno pokazivala na `kronos_remote_repo` umjesto glavnog repozitorija `kronos`.
Zbog toga bi sistemski python odmah pao s exceptionom (`ModuleNotFoundError: No module named chromadb`), a mi smo kao izlaz iz IDE-a dobivali samo šturi string `EOF`.

## Rješenje (Fix)
Zadano je da klijent eksplicitno gađa interpreter iz *venv* direktorija pripadajućeg repozitorija, na pravoj lokaciji:

```json
"command": "e:\\G\\GeminiCLI\\ai-test-project\\kronos\\venv\\Scripts\\python.exe",
"args": [
  "e:\\G\\GeminiCLI\\ai-test-project\\kronos\\src\\mcp_server.py"
]
```

Nakon uređivanja, nužan je obavezni **Reload Window (Ctrl+Shift+P)** kako bi IDE "ubio" staru pogrešnu konekciju i ponovno inicijalizirao vezu s točnim *virtual environment* Pythonom i pravilno digao backend komponente (SQLite i ChromaDB). Vrijeme uspostave i obrade nakon toga postaje instant i performantno. 
