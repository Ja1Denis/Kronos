from mcp.server.fastmcp import FastMCP
import sys

mcp = FastMCP("kronos_simple")

@mcp.tool()
def kronos_ping() -> str:
    return "🏓 pong from simple MCP"

if __name__ == "__main__":
    mcp.run(transport="stdio")
