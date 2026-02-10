
import asyncio
import aiohttp
import os
import time
import random

async def send_ask(session, i):
    """Šalje upit serveru."""
    payload = {"text": f"Upit broj {i}: Kako Kronos radi?", "limit": 3}
    try:
        start = time.time()
        async with session.post('http://localhost:8000/query', json=payload) as resp:
            await resp.json()
            # print(f"🔍 Upit {i} gotov ({time.time()-start:.2f}s)")
            return True
    except Exception as e:
        print(f"❌ Upit {i} greška: {e}")
        return False

async def main():
    print("🔥 POKREĆEM EXTREME STRESS TEST: 'THE INQUISITOR' 🔥")
    
    # 1. Priprema batch datoteka (20 komada)
    if not os.path.exists("docs/extreme_stress"):
        os.makedirs("docs/extreme_stress")
        
    print("📂 Generiram 20 datoteka s miksom sadržaja...")
    for i in range(20):
        with open(f"docs/extreme_stress/file_{i}.py", "w") as f:
            if i % 3 == 0:
                f.write("import requests\n# Namjerna kontradikcija!")
            else:
                f.write(f"# File {i}\nprint('Sve radi u redu u fileu {i}')")
    
    # Wait for watcher to pick up (debounce)
    print("⏳ Čekam Watcher (5s)...")
    await asyncio.sleep(5)

    # 2. Simultano slanje 30 upita dok traje ingest
    async with aiohttp.ClientSession() as session:
        print(f"🚀 Šaljem 30 paralelnih 'ask' upita...")
        tasks = []
        for i in range(30):
            tasks.append(send_ask(session, i))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        
    success_count = sum(1 for r in results if r)
    duration = time.time() - start_time
    
    print(f"\n📊 REZULTATI STRESA:")
    print(f"✅ Uspješnih upita: {success_count}/30")
    print(f"⏱️ Trajanje upita pod opterećenjem: {duration:.2f}s")
    print(f"🧐 Pogledaj monitor za SSE notifikacije od Ingestora/Analitičara!")

if __name__ == "__main__":
    asyncio.run(main())
