
import asyncio
import aiohttp
import os
import time

async def trigger_everything():
    async with aiohttp.ClientSession() as session:
        # 1. Pošalji 3 API posla s različitim trajanjima
        for i in range(3):
            payload = {
                "type": "test_job",
                "params": {"duration": 2 + i, "label": f"Complex-{i}"},
                "priority": 5
            }
            await session.post('http://localhost:8000/jobs', json=payload)
            print(f"🚀 API posao {i} poslan.")
            
    # 2. Kreiraj 5 datoteka za Watcher batch
    print("📂 Kreiram 5 datoteka za Watcher...")
    for i in range(5):
        with open(f"docs/stress/test_{i}.md", "w") as f:
            f.write(f"# Stress Test File {i}\nSadržaj za batch testiranje.")
        time.sleep(0.5) # Malo razmaka, ali unutar 5s debouncea

if __name__ == "__main__":
    asyncio.run(trigger_everything())
