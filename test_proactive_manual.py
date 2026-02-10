
import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

from src.modules.analyst import proactive_analyst

async def manual_test():
    print("🧠 Manual Proactive Analysis Test")
    file_path = "src/forbidden_network_call.py"
    
    if not os.path.exists(file_path):
        print(f"❌ File {file_path} not found!")
        return
        
    print(f"🕵️ Analyzing {file_path}...")
    await proactive_analyst.analyze_ingest([file_path], project="default")
    print("✅ Analysis finished. Check SSE monitor if running.")

if __name__ == "__main__":
    asyncio.run(manual_test())
