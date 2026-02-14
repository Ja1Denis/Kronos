"""
Kronos MCP Bridge - Stdio ↔ SSE Proxy
======================================
Omogućuje VIŠE IDE prozora (Antigravity, Cursor, itd.) 
da koriste ISTI Kronos server istovremeno.

Kako radi:
  IDE (stdio) → Bridge → HTTP POST → Kronos SSE Server
  IDE (stdio) ← Bridge ← SSE events ← Kronos SSE Server

Korištenje u MCP konfiguraciji:
  {
    "mcpServers": {
      "kronos": {
        "command": "python",
        "args": ["E:/G/GeminiCLI/ai-test-project/kronos/src/mcp_bridge.py"]
      }
    }
  }
"""
import sys
import os
import asyncio
import httpx

# Default server URL (može se overridati argumentom ili env varijablom)
DEFAULT_URL = os.environ.get("KRONOS_SSE_URL", "http://localhost:8765")


async def main(server_url: str):
    """Glavni loop: spaja stdio s SSE serverom."""
    
    messages_endpoint = None
    
    # httpx klijent bez timeouta (SSE stream je beskonačan)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=None)
    ) as client:
        
        # --- TASK 1: SSE Reader (Server → stdout) ---
        async def sse_reader():
            nonlocal messages_endpoint
            
            sys.stderr.write(f"[Bridge] Connecting to {server_url}/sse ...\n")
            sys.stderr.flush()
            
            async with client.stream("GET", f"{server_url}/sse") as response:
                if response.status_code != 200:
                    sys.stderr.write(f"[Bridge] SSE connection failed: HTTP {response.status_code}\n")
                    return
                
                sys.stderr.write(f"[Bridge] SSE connected! Waiting for events...\n")
                sys.stderr.flush()
                
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # SSE events are separated by double newlines
                    while "\n\n" in buffer:
                        block, buffer = buffer.split("\n\n", 1)
                        
                        event_type = None
                        data_lines = []
                        
                        for line in block.strip().split("\n"):
                            if line.startswith("event: "):
                                event_type = line[7:]
                            elif line.startswith("data: "):
                                data_lines.append(line[6:])
                            elif line.startswith("data:"):
                                data_lines.append(line[5:])
                        
                        data = "\n".join(data_lines)
                        
                        if event_type == "endpoint":
                            # Server nam šalje endpoint za slanje poruka
                            messages_endpoint = f"{server_url}{data}"
                            sys.stderr.write(f"[Bridge] Messages endpoint: {messages_endpoint}\n")
                            sys.stderr.flush()
                            
                        elif event_type == "message":
                            # Server šalje JSON-RPC odgovor → proslijedi na stdout
                            sys.stdout.write(data + "\n")
                            sys.stdout.flush()
        
        # --- TASK 2: Stdin Reader (stdin → Server) ---
        async def stdin_reader():
            loop = asyncio.get_event_loop()
            
            while True:
                # Čitaj liniju sa stdin-a (blokirajući poziv, zato run_in_executor)
                line = await loop.run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    # stdin zatvoren (IDE je ugašen)
                    sys.stderr.write("[Bridge] stdin closed, shutting down.\n")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Čekaj da imamo endpoint
                wait_count = 0
                while messages_endpoint is None:
                    await asyncio.sleep(0.05)
                    wait_count += 1
                    if wait_count > 200:  # 10 sekundi timeout
                        sys.stderr.write("[Bridge] Timeout waiting for SSE endpoint!\n")
                        break
                
                if messages_endpoint is None:
                    continue
                
                # Pošalji JSON-RPC poruku na server
                try:
                    resp = await client.post(
                        messages_endpoint,
                        content=line,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code not in (200, 202):
                        sys.stderr.write(f"[Bridge] POST error: HTTP {resp.status_code}\n")
                except Exception as e:
                    sys.stderr.write(f"[Bridge] POST exception: {e}\n")
        
        # --- Pokreni oba taska paralelno ---
        try:
            await asyncio.gather(sse_reader(), stdin_reader())
        except Exception as e:
            sys.stderr.write(f"[Bridge] Fatal error: {e}\n")


if __name__ == "__main__":
    # Argument ili environment varijabla za URL
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    
    sys.stderr.write(f"[Bridge] Kronos MCP Bridge starting (target: {url})\n")
    sys.stderr.flush()
    
    try:
        asyncio.run(main(url))
    except KeyboardInterrupt:
        sys.stderr.write("[Bridge] Interrupted.\n")
