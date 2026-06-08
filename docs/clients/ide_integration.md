# Kronos MCP Server - Integracija s Claude Desktop i drugim klijentima

## 🔌 Što je MCP?

**Model Context Protocol (MCP)** je otvoreni standard koji omogućuje AI sustavima poput Claude-a da koriste vanjske alate i pristupaju podacima. Kronos MCP Server pretvara Kronos bazu znanja u alat koji Claude može koristiti direktno.

## 🛠️ Dostupni alati

| Alat | Opis |
|------|------|
| `kronos_search` | Semantička pretraga baze znanja |
| `kronos_stats` | Statistika baze podataka |
| `kronos_decisions` | Dohvaćanje aktivnih odluka |
| `kronos_ingest` | Indeksiranje novih datoteka |

## 🚀 Pokretanje

### Opcija 1: CLI komanda
```bash
cd kronos
python -m src.cli mcp
```

### Opcija 2: Direktno
```bash
cd kronos
python -m src.mcp_server
```

## 🖥️ Integracija s Claude Desktop

1. **Pronađi Claude Desktop konfiguraciju:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. **Dodaj Kronos server u konfiguraciju:**
```json
{
    "mcpServers": {
        "kronos": {
            "command": "python",
            "args": ["-m", "src.mcp_server"],
            "cwd": "E:\\G\\GeminiCLI\\ai-test-project\\kronos"
        }
    }
}
```

3. **Ponovno pokreni Claude Desktop**

4. **Koristi Kronos u razgovoru:**
   - "Pretraži Kronos bazu za 'hybrid search'"
   - "Pokaži statistiku Kronos baze"
   - "Koje su aktivne odluke u projektu?"

## 📋 Primjeri korištenja

### Pretraga
```
Korisnik: Što Kronos zna o vektorskim bazama?
Claude: [koristi kronos_search("vektorske baze")]
        Pronašao sam 5 relevantnih dokumenata...
```

### Statistika
```
Korisnik: Koliko podataka ima u Kronos memoriji?
Claude: [koristi kronos_stats()]
        Baza ima 1,873 datoteka i 11,054 chunkova...
```

### Odluke
```
Korisnik: Koje su trenutno aktivne arhitekturne odluke?
Claude: [koristi kronos_decisions()]
        Pronađeno 2 aktivne odluke...
```

## 🔧 Testiranje

```bash
# Test alata direktno
python -c "from src.mcp_server import kronos_stats; print(kronos_stats())"

# Test pretrage
python -c "from src.mcp_server import kronos_search; print(kronos_search('API', limit=3))"
```

## 📁 Struktura datoteka

```
kronos/
├── src/
│   ├── mcp_server.py          # MCP server implementacija
│   └── cli.py                 # CLI s 'mcp' komandom
├── claude_desktop_config.json # Primjer konfiguracije
└── docs/
    └── mcp_integration.md     # Ova dokumentacija
```

## 🔗 Resursi

- [MCP Specifikacija](https://modelcontextprotocol.io/)
- [FastMCP Python SDK](https://github.com/jlowin/fastmcp)
- [Claude Desktop MCP Docs](https://docs.anthropic.com/en/docs/claude-desktop/mcp)
