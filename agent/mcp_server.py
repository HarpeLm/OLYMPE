"""
Serveur MCP OLYMPE — outils pour le fallback LLM

Outils :
  - get_current_datetime / get_current_date / get_current_time
  - set_timer
  - get_weather (factice, intégration réelle au Palier 7)
  - web_search (SearXNG local — EXCEPTION CONSCIENTE roadmap §7)
"""
from mcp.server import Server
from mcp.types import Tool, TextContent
import datetime
import requests

server = Server("olympe")

SEARXNG_URL = "http://127.0.0.1:8888"

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_datetime",
            description="Retourne la date et l'heure actuelles complètes",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_current_date",
            description="Retourne uniquement la date d'aujourd'hui",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_current_time",
            description="Retourne uniquement l'heure actuelle",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="set_timer",
            description="Démarre un minuteur pour une durée donnée",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Durée en minutes"},
                    "label": {"type": "string", "description": "Nom optionnel du minuteur"}
                },
                "required": ["duration_minutes"]
            }
        ),
        Tool(
            name="get_weather",
            description="Récupère la météo actuelle pour une ville",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nom de la ville"}
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="web_search",
            description="Recherche sur internet via l'instance SearXNG locale (EXCEPTION CONSCIENTE roadmap §7 : requête sortante acceptée)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La requête de recherche"}
                },
                "required": ["query"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handler MCP 1.29.1 : name et arguments sont passés directement."""
    
    if name == "get_current_datetime":
        now = datetime.datetime.now()
        return [TextContent(type="text", text=now.strftime("%A %d %B %Y, %H:%M:%S"))]

    elif name == "get_current_date":
        now = datetime.datetime.now()
        return [TextContent(type="text", text=now.strftime("%A %d %B %Y"))]

    elif name == "get_current_time":
        now = datetime.datetime.now()
        return [TextContent(type="text", text=now.strftime("%H:%M"))]

    elif name == "set_timer":
        duration = arguments.get("duration_minutes", 0)
        label = arguments.get("label", "Minuteur")
        return [TextContent(type="text", text=f"{label} démarré pour {duration} minutes")]

    elif name == "get_weather":
        city = arguments.get("city", "inconnue")
        return [TextContent(type="text", text=f"Météo à {city} : 18°C, ensoleillé (donnée factice, intégration réelle au Palier 7)")]

    elif name == "web_search":
        query = arguments.get("query", "")
        try:
            resp = requests.get(
                f"{SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
                timeout=8,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])[:3]
            if not results:
                return [TextContent(type="text", text=f"Aucun résultat pour : {query}")]
            summary = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:120]}"
                for r in results
            )
            return [TextContent(type="text", text=f"Résultats pour '{query}':\n{summary}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Erreur SearXNG : {e}")]

    raise ValueError(f"Outil inconnu : {name}")

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
