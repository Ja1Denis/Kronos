
import asyncio
import aiohttp
import json
import uuid

async def listen_sse():
    print("📡 Connecting to SSE stream...")
    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get('http://localhost:8000/stream') as response:
            print("✅ Connected! Waiting for events...")
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                
                if line.startswith('event:'):
                    event_type = line.split(':')[1].strip()
                    print(f"\n📩 Event: {event_type}")
                elif line.startswith('data:'):
                    try:
                        # Ponekad podaci mogu biti u više linija, ali ovdje je jednostavno
                        data_str = line[5:].strip()
                        data = json.loads(data_str)
                        print(f"📦 Data: {json.dumps(data, indent=2)}")
                        
                        # Stop test if complete
                        if data.get('status') == 'completed':
                            print("\n🏁 Job completed. Closing connection.")
                            # Exit loop/program
                            return
                    except Exception as e:
                        print(f"⚠️ Failed to parse data: {data_str} | Error: {e}")

async def trigger_job():
    # Wait a bit for listener to connect
    await asyncio.sleep(2)
    print("\n🚀 Triggering a test job via API...")
    
    async with aiohttp.ClientSession() as session:
        job_id = str(uuid.uuid4())
        payload = {
            "type": "test_job",
            "params": {"duration": 3},
            "priority": 5
        }
        async with session.post(f'http://localhost:8000/jobs', json=payload) as resp:
            data = await resp.json()
            print(f"✅ Job submitted: {data}")

async def main():
    # Run listener and trigger in parallel
    await asyncio.gather(
        listen_sse(),
        trigger_job()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest stopped.")
