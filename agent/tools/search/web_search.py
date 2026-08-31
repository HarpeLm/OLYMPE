"""Outil : recherche web via SearXNG local."""
import json
import urllib.parse
import urllib.request

SEARXNG_URL = "http://127.0.0.1:8888"

TOOL = {
    "name": "web_search",
    "description": "Recherche internet via l'instance SearXNG locale.",
    "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Requete"}},
        "required": ["query"]
    }
}

def run(args):
    query = args.get("query", "")
    try:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        req = urllib.request.Request(f"{SEARXNG_URL}/search?{params}")
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
    except (OSError, ValueError):
        return "SearXNG local injoignable (127.0.0.1:8888)."
    res = data.get("results", [])[:3]
    if not res:
        return f"Aucun resultat pour : {query}"
    return "\n".join(f"- {r.get('title', '')}: {r.get('content', '')[:120]}"
                     for r in res)
