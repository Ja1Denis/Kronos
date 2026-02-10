import asyncio
import os
import sys
import json

# Add root to sys.path
sys.path.append(os.getcwd())

from src.mcp_server import kronos_stats, kronos_submit_job, kronos_list_jobs, kronos_job_status

async def test_mcp_flow():
    print("--- 1. TEST: kronos_stats ---")
    stats = kronos_stats()
    print(stats)
    print("\n" + "="*50 + "\n")

    print("--- 2. TEST: kronos_submit_job ---")
    # Šaljemo test_job koji traje 2 sekunde
    submit_msg = kronos_submit_job(
        job_type="test_job", 
        params={"duration": 2, "reason": "MCP Integration Test"},
        priority=8
    )
    print(submit_msg)
    
    # Izvuci ID iz poruke (format: ID: `uuid`.)
    try:
        job_id = submit_msg.split("ID: `")[1].split("`")[0]
        print(f"Detektiran Job ID: {job_id}")
    except:
        print("Greška pri ekstrakciji Job ID-a!")
        return

    print("\n" + "="*50 + "\n")

    print("--- 3. TEST: kronos_list_jobs ---")
    job_list = kronos_list_jobs(limit=5)
    print(job_list)
    
    print("\n" + "="*50 + "\n")

    print("--- 4. TEST: kronos_job_status ---")
    status = kronos_job_status(job_id)
    print(status)

if __name__ == "__main__":
    asyncio.run(test_mcp_flow())
