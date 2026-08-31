"""OLYMPE — point d'entrée unique (mode écrit).
Tape une phrase, tout est routé :
  [1] dispatcheur regex -> action TaHoma immédiate (0 LLM)
  [2] LLM + tool-calling local : heure, minuteur, notes, météo,
      calendrier, mémoire, recherche, volets...
  [3] réponse finale affichée
'q' pour quitter. Stdlib uniquement, tourne avec python3 système."""
import datetime
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from router.orchestrator import orchestrate

LLM_URL = "http://127.0.0.1:8000/v1/chat/completions"
SEARXNG_URL = "http://127.0.0.1:8888"
NOTES_DIR = ROOT / "data" / "notes"

SYS = ("Tu es Olympe, assistant personnel local. Réponds brièvement, "
       "en français, comme à l'oral. Utilise les outils quand nécessaire.")

TOOLS = [
    {"type": "function", "function": {"name": "get_current_time",
     "description": "Heure actuelle", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_current_date",
     "description": "Date d'aujourd'hui", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "set_timer",
     "description": "Minuteur réel avec annonce vocale à la fin",
     "parameters": {"type": "object", "properties": {
         "duration_minutes": {"type": "integer", "description": "Durée en minutes"},
         "duration_seconds": {"type": "integer", "description": "Durée en secondes (prioritaire)"},
         "label": {"type": "string", "description": "Nom du minuteur"}}, "required": []}}},
    {"type": "function", "function": {"name": "get_system_info",
     "description": "Batterie et espace disque du Mac",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "create_note",
     "description": "Enregistre une note texte",
     "parameters": {"type": "object", "properties": {
         "title": {"type": "string"}, "content": {"type": "string"}},
         "required": ["content"]}}},
    {"type": "function", "function": {"name": "list_notes",
     "description": "Liste les notes récentes",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_weather",
     "description": "Météo actuelle d'une ville",
     "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
     "required": ["city"]}}},
    {"type": "function", "function": {"name": "web_search",
     "description": "Recherche internet (SearXNG local)",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
     "required": ["query"]}}},
    {"type": "function", "function": {"name": "create_calendar_event",
     "description": "Crée un événement au Calendrier Apple",
     "parameters": {"type": "object", "properties": {
         "title": {"type": "string"}, "date": {"type": "string"},
         "time": {"type": "string"}}, "required": ["title"]}}},
    {"type": "function", "function": {"name": "get_next_calendar_event",
     "description": "Prochain événement du Calendrier Apple",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "list_shutters",
     "description": "Liste les volets Somfy et leur état",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "open_shutters",
     "description": "Ouvre un volet par son nom",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}},
     "required": ["name"]}}},
    {"type": "function", "function": {"name": "close_shutters",
     "description": "Ferme un volet par son nom",
     "parameters": {"type": "object", "properties": {"name": {"type": "string"}},
     "required": ["name"]}}},
    {"type": "function", "function": {"name": "remember",
     "description": "Mémorise un fait durable",
     "parameters": {"type": "object", "properties": {
         "content": {"type": "string"}, "category": {"type": "string"}},
     "required": ["content"]}}},
    {"type": "function", "function": {"name": "recall",
     "description": "Recherche dans les faits mémorisés",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}}},
]


def _searxng(query):
    params = urllib.parse.urlencode({"q": query, "format": "json"})
    req = urllib.request.Request(f"{SEARXNG_URL}/search?{params}")
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())


def run_tool(name, args):
    """Exécute un outil localement (mêmes comportements que le MCP)."""
    now = datetime.datetime.now()
    if name == "get_current_time":
        return now.strftime("%H:%M")
    if name == "get_current_date":
        return now.strftime("%A %d %B %Y")
    if name == "set_timer":
        minutes = int(args.get("duration_minutes", 0) or 0)
        seconds = int(args.get("duration_seconds", 0) or 0) or minutes * 60
        label = re.sub(r"[^a-zA-Z0-9 àéèêç-]", "", args.get("label", "Minuteur"))
        if seconds <= 0:
            return "Durée invalide."
        cmd = (f"sleep {seconds} && (say -v Thomas 'Minuteur {label} terminé' "
               f"|| say 'Minuteur {label} terminé')")
        subprocess.Popen(["bash", "-c", cmd], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        duree = f"{minutes} minutes" if minutes else f"{seconds} secondes"
        return f"{label} démarré pour {duree}."
    if name == "get_system_info":
        parts = []
        try:
            out = subprocess.run(["pmset", "-g", "batt"], capture_output=True,
                                 text=True, timeout=3).stdout
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
        return ", ".join(parts) or "infos système indisponibles"
    if name == "create_note":
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_",
                      (args.get("title") or "note").lower()).strip("_")[:30] or "note"
        fname = now.strftime("%Y-%m-%d_%H%M") + "_" + slug + ".txt"
        (NOTES_DIR / fname).write_text(args.get("content", ""), encoding="utf-8")
        return f"Note enregistrée : {fname}"
    if name == "list_notes":
        if not NOTES_DIR.exists():
            return "Aucune note."
        files = sorted(NOTES_DIR.glob("*.txt"), reverse=True)[:5]
        return "Notes : " + ", ".join(f.name for f in files) if files else "Aucune note."
    if name == "get_weather":
        city = args.get("city", "Paris")
        try:
            # Géocodage simple
            geo_req = urllib.request.Request(
                f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=fr")
            with urllib.request.urlopen(geo_req, timeout=5) as r:
                geo = json.loads(r.read().decode())
            if not geo.get("results"):
                return f"Ville introuvable : {city}"
            loc = geo["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            # Météo actuelle
            weather_req = urllib.request.Request(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto")
            with urllib.request.urlopen(weather_req, timeout=5) as r:
                weather = json.loads(r.read().decode())
            curr = weather["current"]
            temp = curr["temperature_2m"]
            wind = curr["wind_speed_10m"]
            code = curr["weather_code"]
            # Traduction simple des codes météo
            codes = {0: "ciel dégagé", 1: "principalement dégagé", 2: "partiellement nuageux",
                     3: "couvert", 45: "brouillard", 48: "brouillard givrant",
                     51: "bruine légère", 53: "bruine modérée", 55: "bruine dense",
                     61: "pluie légère", 63: "pluie modérée", 65: "pluie forte",
                     71: "neige légère", 73: "neige modérée", 75: "neige forte",
                     80: "averses légères", 81: "averses modérées", 82: "averses violentes",
                     95: "orage", 96: "orage avec grêle"}
            desc = codes.get(code, "conditions variables")
            return f"{city} : {temp}°C, {desc}, vent {wind} km/h"
        except Exception as e:
            return f"Erreur météo : {e}"
    if name == "web_search":
        data = _searxng(args.get("query", ""))
        res = data.get("results", [])[:3]
        if not res:
            return "Aucun résultat."
        return "\n".join(f"- {r.get('title', '')}: {r.get('content', '')[:120]}"
                         for r in res)
    if name == "create_calendar_event":
        from integrations.apple_calendar import create_event
        return create_event(title=args.get("title"), date=args.get("date"),
                            time=args.get("time"))
    if name == "get_next_calendar_event":
        from integrations.apple_calendar import get_next_event
        return get_next_event()
    if name == "list_shutters":
        from integrations.tahoma import list_shutters as ls
        return ", ".join(
            f"{s['name']} ({'fermé' if s['closure'] == 100 else 'ouvert' if s['closure'] == 0 else str(100 - s['closure']) + '% ouvert'})"
            for s in ls())
    if name == "open_shutters":
        from integrations.tahoma import open_shutter
        return open_shutter(args.get("name", ""))["message"]
    if name == "close_shutters":
        from integrations.tahoma import close_shutter
        return close_shutter(args.get("name", ""))["message"]
    if name == "remember":
        from agent.memory import Memory
        m = Memory()
        fid = m.remember(args.get("content", ""), args.get("category", "general"))
        m.close()
        return f"C'est noté (id={fid})."
    if name == "recall":
        from agent.memory import Memory
        m = Memory()
        res = m.recall(query=args.get("query"), limit=5)
        m.close()
        return ("Souvenirs : " + " ; ".join(r["content"] for r in res)
                if res else "Aucun souvenir.")
    return f"Outil inconnu : {name}"


def post_chat(messages):
    payload = {"model": "local", "messages": messages, "tools": TOOLS,
               "max_tokens": 512, "temperature": 0.7}
    req = urllib.request.Request(
        LLM_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def llm_with_tools(text):
    """Boucle agent : le 8B choisit des outils, on les exécute, il conclut."""
    messages = [{"role": "system", "content": SYS},
                {"role": "user", "content": text}]
    for _ in range(4):
        data = post_chat(messages)
        msg = data["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or ""
        assistant = {"role": "assistant", "content": msg.get("content") or "",
                     "tool_calls": calls}
        if msg.get("reasoning_content"):
            assistant["reasoning_content"] = msg["reasoning_content"]
        messages.append(assistant)
        for c in calls:
            fn = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = run_tool(fn, args)
            except Exception as e:
                result = f"Erreur : {e}"
            print(f"   [outil] {fn}")
            messages.append({"role": "tool", "tool_call_id": c.get("id", ""),
                             "name": fn, "content": str(result)})
    return "(trop d'étapes, je m'arrête là)"


print("OLYMPE (mj.py) — écris une phrase, 'q' pour quitter")
while True:
    try:
        phrase = input("\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAu revoir.")
        break
    if not phrase or phrase.lower() == "q":
        print("Au revoir.")
        break
    try:
        result = orchestrate(phrase)
        if result["handled"]:
            print("  →", result["result"]["message"])
        else:
            print("  →", llm_with_tools(phrase))
    except Exception as e:
        print("  Erreur :", e)
