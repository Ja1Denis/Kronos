import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

from src.mcp_server import mcp

async def main():
    try:
        tools = await mcp.list_tools()
        print("MCP tools:", [t.name for t in tools])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
