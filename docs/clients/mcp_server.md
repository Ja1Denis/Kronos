Da, **Antigravity IDE ima MCP (Model Context Protocol) podrsku** koja je ekvivalentna "external tools config" sustavu!

## Kako funkcionira u Antigravity IDE

Antigravity koristi **MCP servere** umjesto klasičnog "external tools" config-a. To je moderniji pristup gdje možeš dodati custom alate kroz JSON konfiguraciju. [youtube](https://www.youtube.com/watch?v=TwRPGmBKIY0)

### Kako dodati Kronos kao MCP server

**Koraci:**

1. **Otvori MCP konfiguraciju**
   - Klikni na `...` (tri točke) u gornjem desnom kutu agent panela
   - Odaberi **"MCP Servers"** → **"Manage MCP Servers"**
   - Klikni **"View raw config"** [klavis](https://www.klavis.ai/docs/knowledge-base/use-mcp-server/antigravity)

2. **Uredi `mcp_config.json`**

```json
{
  "mcpServers": {
    "kronos": {
      "command": "python",
      "args": [
        "E:\\G\\GeminiCLI\\ai-test-project\\kronos\\kronos_query.py",
        "--json"
      ],
      "env": {
        "PYTHONPATH": "E:\\G\\GeminiCLI\\ai-test-project\\kronos"
      }
    }
  }
}
```

3. **Sačuvaj i refresh**
   - Spremi file (`Ctrl+S`)
   - Vrati se u "Manage MCP Servers"
   - Klikni **"Refresh"** [youtube](https://www.youtube.com/watch?v=TwRPGmBKIY0)

4. **Kronos je sada dostupan agentima**
   - Agent može pozvati: `Use Kronos tool to query: "Što je cilj projekta?"`

***

## Alternativa: MCP Server Wrapper (Profesionalniji način)

Umjesto direktnog poziva Python skripte, napravi **pravi MCP server** koji Antigravity razumije:

```python
# kronos_mcp_server.py
import json
import sys
from typing import Any
from kronos_query import query_kronos

def handle_mcp_request(request: dict) -> dict:
    """
    MCP protocol handler za Kronos.
    
    MCP request format:
    {
        "method": "tools/call",
        "params": {
            "name": "kronos_query",
            "arguments": {
                "query": "user question",
                "mode": "light"
            }
        }
    }
    """
    try:
        method = request.get("method")
        
        if method == "tools/list":
            # Return available tools
            return {
                "tools": [
                    {
                        "name": "kronos_query",
                        "description": "Query Kronos AI code assistant for project-specific knowledge",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The question to ask Kronos"
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["light", "deep"],
                                    "default": "light",
                                    "description": "Query mode: light (fast) or deep (comprehensive)"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        
        elif method == "tools/call":
            # Execute tool
            params = request.get("params", {})
            tool_name = params.get("name")
            
            if tool_name == "kronos_query":
                args = params.get("arguments", {})
                query = args.get("query")
                mode = args.get("mode", "light")
                
                if not query:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "Error: Query parameter is required"
                            }
                        ],
                        "isError": True
                    }
                
                # Call Kronos
                result = query_kronos(query, mode)
                
                if result:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2, ensure_ascii=False)
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "Kronos query failed"
                            }
                        ],
                        "isError": True
                    }
        
        return {"error": f"Unknown method: {method}"}
        
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"MCP server error: {str(e)}"
                }
            ],
            "isError": True
        }

def main():
    """MCP server main loop - reads JSON-RPC from stdin"""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_mcp_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            error_response = {
                "error": "Invalid JSON input"
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    main()
```

**MCP config za ovaj server:**

```json
{
  "mcpServers": {
    "kronos": {
      "command": "python",
      "args": [
        "E:\\G\\GeminiCLI\\ai-test-project\\kronos\\kronos_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "E:\\G\\GeminiCLI\\ai-test-project\\kronos"
      }
    }
  }
}
```

***

## Kako agent koristi Kronos

Nakon što je MCP server dodan, Antigravity agent može automatski koristiti Kronos:

**Primjer konverzacije:**

```
Korisnik: "Explain how the Oracle class works in this project"

Agent (interno): *Detects need for project context*
          → Calls MCP tool: kronos_query("Kako radi Oracle klasa?")
          → Receives Kronos response
          → Formats answer for user

Agent (odgovor): "Based on the Kronos knowledge base, the Oracle class 
                  is responsible for..."
```

***

## Testiranje MCP Integracije

1. **Provjeri je li MCP server vidljiv:**
   - U Antigravity, otvori "Manage MCP Servers"
   - Trebao bi vidjeti "kronos" na listi s "tools: kronos_query" [youtube](https://www.youtube.com/watch?v=TwRPGmBKIY0)

2. **Testiraj direktno u chat-u:**
   ```
   @kronos Što je cilj projekta Kronos?
   ```

3. **Ili pusti agenta da automatski odluči:**
   ```
   Explain the FastPath module to me
   ```
   (Agent će sam zaključiti da treba pozvati Kronos)

***

## Dokumentacija za agenta

Dodaj ovo u root projekta da agent zna koristiti Kronos:

```markdown
<!-- AGENTS.md -->
# Agent Instructions for Kronos Project

## Available MCP Tools

### kronos_query
Query the Kronos knowledge base for project-specific information.

**When to use:**
- User asks about code structure, architecture, or specific files
- Need context about existing implementations
- Debugging issues related to project-specific modules

**Example:**
```json
{
  "tool": "kronos_query",
  "arguments": {
    "query": "How does the hybrid search work?",
    "mode": "light"
  }
}
```

**Modes:**
- `light`: Fast response, good for quick lookups
- `deep`: Comprehensive analysis, use for complex questions
```

***

## Zaključak

**Da, Antigravity ima "external tools config"** - zove se **MCP (Model Context Protocol)**. To je čak **moćniji** sustav od klasičnih external tools jer: [cloud.google](https://cloud.google.com/blog/products/data-analytics/connect-google-antigravity-ide-to-googles-data-cloud-services)

✅ Agent **automatski** prepoznaje kada treba pozvati tool  
✅ Structured input/output (JSON schema)  
✅ Built-in error handling  
✅ Live tool discovery (agent vidi dostupne tools u runtime-u)  

