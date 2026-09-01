"""
Serveur MCP MJ — adaptateur mince.
Toute la logique des outils vit dans agent/tools/.
Ce serveur expose juste le catalogue via MCP et route les appels."""
import sys
from pathlib import Path

# Ajouter la racine du projet au path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server import Server
from mcp.types import Tool, TextContent
from agent.tools import list_tools, run_tool

server = Server("olympe")


@server.list_tools()
async def list_tools_handler() -> list[Tool]:
    """Expose le catalogue d'outils depuis agent/tools/."""
    return [Tool(**t) for t in list_tools()]


@server.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
    """Route un appel d'outil vers agent/tools.run_tool."""
    arguments = arguments or {}
    try:
        result = run_tool(name, arguments)
    except Exception as e:
        result = f"Erreur : {e}"
    return [TextContent(type="text", text=str(result))]


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    asyncio.run(main())
