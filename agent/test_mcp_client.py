"""
Client de test : se connecte au serveur MCP OLYMPE en stdio,
liste les outils et appelle get_current_datetime.
"""
import asyncio

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


async def main():
    params = StdioServerParameters(
        command="/Users/harpepluie/O.L.Y/OLYMPE/.venv/bin/python",
        args=["/Users/harpepluie/O.L.Y/OLYMPE/agent/mcp_server.py"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Outils exposes :", [t.name for t in tools.tools])

            result = await session.call_tool("get_current_datetime", {})
            for block in result.content:
                print("Resultat :", getattr(block, "text", block))


asyncio.run(main())
