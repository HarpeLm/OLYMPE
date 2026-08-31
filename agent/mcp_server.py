"""
Serveur MCP OLYMPE — outils pour le fallback LLM (catalogue v2 : 9 outils)

Temps    : get_current_datetime / get_current_date / get_current_time
Minuteur : set_timer (REEL : sous-processus detache sleep + say)
Systeme  : get_system_info (batterie + disque, lecture seule)
Notes    : create_note / list_notes (artefacts dans data/notes/)
Externe  : get_weather + web_search via SearXNG local
           (EXCEPTION CONSCIENTE roadmap §7, contenue dans SearXNG)
"""
import datetime
import re
import shutil
import subprocess
from pathlib import Path

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("olympe")

SEARXNG_URL = "http://127.0.0.1:8888"
ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "data" / "notes"


def _searxng(query):
    resp = requests.get(
        f"{SEARXNG_URL}/search",
        params={"q": query, "format": "json"},
        timeout=8,
    )
    resp.raise_for_status()
    return resp.json()


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
            description="Démarre un vrai minuteur : une voix macOS annonce la fin",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Durée en minutes"},
                    "duration_seconds": {"type": "integer", "description": "Durée en secondes (prioritaire si présent)"},
                    "label": {"type": "string", "description": "Nom optionnel du minuteur"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_system_info",
            description="Retourne la batterie et l'espace disque libre du Mac",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="create_note",
            description="Enregistre une note texte dans data/notes/",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titre court de la note"},
                    "content": {"type": "string", "description": "Contenu de la note"}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="list_notes",
            description="Liste les 5 notes les plus récentes",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_weather",
            description="Récupère la météo actuelle pour une ville (via SearXNG local)",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Nom de la ville"}
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="remember",
            description="Mémorise un fait durable (préférence, info personnelle)",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Le fait à mémoriser"},
                    "category": {"type": "string", "description": "Catégorie (préférence, info, etc.)"}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="recall",
            description="Recherche dans les faits mémorisés",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Mot-clé de recherche"},
                    "category": {"type": "string", "description": "Filtrer par catégorie"}
                },
                "required": []
            }
        ),
        Tool(
            name="forget",
            description="Oublie un fait mémorisé (par son id)",
            inputSchema={
                "type": "object",
                "properties": {
                    "fact_id": {"type": "integer", "description": "ID du fait à oublier"}
                },
                "required": ["fact_id"]
            }
        ),
        Tool(
            name="create_calendar_event",
            description="Crée un événement dans le Calendrier Apple (calendrier Olympe)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titre de l'événement"},
                    "date": {"type": "string", "description": "aujourd'hui / demain / vendredi / 28/08"},
                    "time": {"type": "string", "description": "ex: 14h30 ou 14:30"}
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="get_next_calendar_event",
            description="Prochain événement du Calendrier Apple (7 prochains jours)",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_todays_events",
            description="Événements du jour dans le Calendrier Apple",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="web_search",
            description="Recherche sur internet via l'instance SearXNG locale (EXCEPTION CONSCIENTE roadmap §7)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La requête de recherche"}
                },
                "required": ["query"]
            }
        ),
            Tool(
            name="list_shutters",
            description="Liste les volets Somfy de la maison avec leur état actuel (ouvert/fermé/pourcentage)",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="open_shutters",
            description="Ouvre complètement un volet Somfy par son nom (ex: Cuisine, Bureau, Chambre Fabian, Baie 1)",
            inputSchema={"type": "object", "properties": {"name": {"type": "string", "description": "Nom du volet"}}, "required": ["name"]}
        ),
        Tool(
            name="close_shutters",
            description="Ferme complètement un volet Somfy par son nom",
            inputSchema={"type": "object", "properties": {"name": {"type": "string", "description": "Nom du volet"}}, "required": ["name"]}
        ),
        Tool(
            name="set_shutter_position",
            description="Positionne un volet Somfy à un pourcentage d'ouverture (0=fermé, 100=ouvert)",
            inputSchema={"type": "object", "properties": {"name": {"type": "string", "description": "Nom du volet"}, "percent": {"type": "integer", "description": "Pourcentage d'ouverture (0-100)"}}, "required": ["name", "percent"]}
        ),
        Tool(
            name="open_all_shutters",
            description="Ouvre tous les volets de la maison",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="close_all_shutters",
            description="Ferme tous les volets de la maison",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    arguments = arguments or {}

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
        minutes = int(arguments.get("duration_minutes", 0) or 0)
        seconds = int(arguments.get("duration_seconds", 0) or 0) or minutes * 60
        label = re.sub(r"[^a-zA-Z0-9 àéèêç-]", "", arguments.get("label", "Minuteur"))
        if seconds <= 0:
            return [TextContent(type="text", text="Durée invalide.")]
        # Sous-processus DETACHE : survit à la fermeture du serveur MCP
        cmd = f"sleep {seconds} && (say -v Thomas 'Minuteur {label} terminé' || say 'Minuteur {label} terminé')"
        subprocess.Popen(
            ["bash", "-c", cmd],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        duree = f"{minutes} minutes" if minutes else f"{seconds} secondes"
        return [TextContent(type="text", text=f"{label} démarré pour {duree}. Une voix te préviendra à la fin.")]

    elif name == "get_system_info":
        parts = []
        try:
            out = subprocess.run(
                ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=3
            ).stdout
            m = re.search(r"(\d+)\s*%", out)
            if m:
                state = "en charge" if "AC Power" in out else "sur batterie"
                parts.append(f"batterie {m.group(1)} % ({state})")
        except Exception:
            pass
        try:
            du = shutil.disk_usage("/")
            parts.append(f"disque libre {du.free // (1024**3)} Go")
        except Exception:
            pass
        text = ", ".join(parts) if parts else "informations système indisponibles"
        return [TextContent(type="text", text=text)]

    elif name == "create_note":
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        content = arguments.get("content", "")
        title = arguments.get("title", "note")
        ts = datetime.datetime.now()
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:30] or "note"
        fname = ts.strftime("%Y-%m-%d_%H%M") + "_" + slug + ".txt"
        (NOTES_DIR / fname).write_text(content, encoding="utf-8")
        return [TextContent(type="text", text=f"Note enregistrée : {fname}")]

    elif name == "list_notes":
        if not NOTES_DIR.exists():
            return [TextContent(type="text", text="Aucune note pour l'instant.")]
        files = sorted(NOTES_DIR.glob("*.txt"), reverse=True)[:5]
        if not files:
            return [TextContent(type="text", text="Aucune note pour l'instant.")]
        return [TextContent(type="text", text="Notes récentes : " + ", ".join(f.name for f in files))]

    elif name == "get_weather":
        city = arguments.get("city", "Paris")
        try:
            data = _searxng(f"météo {city} aujourd'hui")
            results = data.get("results", [])
            if not results:
                return [TextContent(type="text", text=f"Pas de météo trouvée pour {city}.")]
            return [TextContent(type="text", text=f"Météo {city} : {results[0].get('content', '')[:200]}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Erreur météo : {e}")]

    elif name == "remember":
        try:
            from agent.memory import Memory
        except ImportError:
            from memory import Memory
        m = Memory()
        fid = m.remember(arguments.get("content", ""), arguments.get("category", "general"))
        m.close()
        return [TextContent(type="text", text=f"C'est noté, je m'en souviendrai (id={fid}).")]

    elif name == "recall":
        try:
            from agent.memory import Memory
        except ImportError:
            from memory import Memory
        m = Memory()
        results = m.recall(query=arguments.get("query"), category=arguments.get("category"), limit=5)
        m.close()
        if not results:
            return [TextContent(type="text", text="Je n'ai aucun souvenir correspondant.")]
        return [TextContent(type="text", text="Souvenirs : " + " ; ".join(
            f"{r['content']} [{r['category']}]" for r in results))]

    elif name == "forget":
        try:
            from agent.memory import Memory
        except ImportError:
            from memory import Memory
        m = Memory()
        m.forget(arguments.get("fact_id", 0))
        m.close()
        return [TextContent(type="text", text="C'est oublié.")]

    elif name == "create_calendar_event":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.apple_calendar import create_event
        return [TextContent(type="text", text=create_event(
            title=arguments.get("title"), date=arguments.get("date"),
            time=arguments.get("time")))]

    elif name == "get_next_calendar_event":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.apple_calendar import get_next_event
        return [TextContent(type="text", text=get_next_event())]

    elif name == "get_todays_events":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.apple_calendar import get_events_today
        return [TextContent(type="text", text=get_events_today())]

    elif name == "web_search":
        query = arguments.get("query", "")
        try:
            data = _searxng(query)
            results = data.get("results", [])[:3]
            if not results:
                return [TextContent(type="text", text=f"Aucun résultat pour : {query}")]
            summary = "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:120]}"
                for r in results
            )
            return [TextContent(type="text", text=f"Résultats pour '{query}':\n{summary}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Erreur SearXNG : {e}")]

    elif name == "list_shutters":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import list_shutters as _tahoma_list
        lignes = []
        for s in _tahoma_list():
            c = s["closure"]
            pos = "ferme" if c == 100 else ("ouvert" if c == 0 else str(100 - c) + "% ouvert")
            lignes.append(s["name"] + " (" + pos + ")")
        return [TextContent(type="text", text="Volets : " + ", ".join(lignes))]
    elif name == "open_shutters":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import open_shutter
        try:
            r = open_shutter(arguments.get("name", ""))
        except ValueError as e:
            r = {"success": False, "message": str(e)}
        return [TextContent(type="text", text=r["message"])]
    elif name == "close_shutters":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import close_shutter
        try:
            r = close_shutter(arguments.get("name", ""))
        except ValueError as e:
            r = {"success": False, "message": str(e)}
        return [TextContent(type="text", text=r["message"])]
    elif name == "set_shutter_position":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import set_shutter_position
        try:
            r = set_shutter_position(arguments.get("name", ""), int(arguments.get("percent", 50)))
        except ValueError as e:
            r = {"success": False, "message": str(e)}
        return [TextContent(type="text", text=r["message"])]
    elif name == "open_all_shutters":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import list_shutters as _tahoma_list, open_shutter
        for s in _tahoma_list():
            open_shutter(s["name"])
        return [TextContent(type="text", text="Tous les volets sont en cours d'ouverture.")]
    elif name == "close_all_shutters":
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from integrations.tahoma import list_shutters as _tahoma_list, close_shutter
        for s in _tahoma_list():
            close_shutter(s["name"])
        return [TextContent(type="text", text="Tous les volets sont en cours de fermeture.")]
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
