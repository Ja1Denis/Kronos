import asyncio
import os
import sys
import time
import concurrent.futures
from src.mcp_server import kronos_submit_job, kronos_stats, kronos_list_jobs

# Add root to sys.path
sys.path.append(os.getcwd())

async def submit_burst(count=50):
    print(f"🚀 Šaljem burst od {count} poslova...")
    loop = asyncio.get_event_loop()
    
    # Koristimo ThreadPoolExecutor jer su MCP funkcije sinkrone (ali rade s DB)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(count):
            futures.append(loop.run_in_executor(
                executor, 
                kronos_submit_job, 
                "stress_test", 
                {"id": i, "timestamp": time.time()}, 
                i % 10 + 1 # Različiti prioriteti (1-10)
            ))
        
        results = await asyncio.gather(*futures, return_exceptions=True)
        
    success = [r for r in results if isinstance(r, str) and "uspješno poslan" in r]
    errors = [r for r in results if not isinstance(r, str) or "uspješno poslan" not in r]
    
    print(f"✅ Uspješno poslano: {len(success)}")
    if errors:
        print(f"❌ Greške: {len(errors)}")
        for e in errors[:5]: # Prikazi prvih 5 grešaka
            print(f"   -> {e}")
    return len(errors) == 0

async def rapid_read_test(duration=5):
    print(f"📈 Pokrećem agresivno čitanje (stats/list) tijekom {duration} sekundi...")
    end_time = time.time() + duration
    reads = 0
    errors = 0
    
    while time.time() < end_time:
        try:
            kronos_stats()
            kronos_list_jobs(limit=20)
            reads += 2
        except Exception as e:
            errors += 1
            print(f"‼️ Greška pri čitanju: {e}")
        time.sleep(0.1)
        
    print(f"📊 Ukupno uspješnih čitanja: {reads}")
    print(f"‼️ Ukupno grešaka pri čitanju: {errors}")
    return errors == 0

async def main():
    start_total = time.time()
    
    # 1. Čisto čitanje pod opterećenjem
    print("\n--- FAZA 1: Burst Submission ---")
    sub_success = await submit_burst(50)
    
    # 2. Paralelno Submit + Read
    print("\n--- FAZA 2: Simultano Submit & Read (Stress) ---")
    await asyncio.gather(
        submit_burst(20),
        rapid_read_test(3)
    )
    
    duration = time.time() - start_total
    print(f"\n🏁 Stress test završen u {duration:.2f}s")
    
    # Konačna statistika
    print("\nKonačna provjera stanja:")
    print(kronos_stats())

if __name__ == "__main__":
    asyncio.run(main())
