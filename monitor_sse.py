
import asyncio
import aiohttp
import json
import time

async def monitor():
    print("📡 Monitor spojen na Kronos SSE stream...")
    
    timeout = aiohttp.ClientTimeout(total=None)
    while True:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('http://localhost:8000/stream') as response:
                    print("✅ Konekcija uspostavljena. Čekam događaje...")
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line: continue
                        
                        if line.startswith('event:'):
                            event_type = line.split(':')[1].strip()
                            print(f"\n🔔 DOGAĐAJ: {event_type}")
                        elif line.startswith('data:'):
                            try:
                                data = json.loads(line[5:].strip())
                                print(f"📦 PODACI: {json.dumps(data, indent=2)}")
                            except:
                                print(f"📦 RAW: {line}")
        except Exception as e:
            print(f"❌ Konekcija izgubljena ({e}). Rekonekcija za 2s...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\nMonitor zaustavljen.")
