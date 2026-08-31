"""Outil : météo actuelle d'une ville (Open-Meteo, sans clé API)."""
import json
import urllib.parse
import urllib.request

TOOL = {
    "name": "get_weather",
    "description": "Météo actuelle d'une ville : température, conditions, vent.",
    "inputSchema": {
        "type": "object",
        "properties": {"city": {"type": "string", "description": "Nom de la ville"}},
        "required": ["city"]
    }
}

CODES_FR = {0: "ciel degage", 1: "principalement degage", 2: "partiellement nuageux",
            3: "couvert", 45: "brouillard", 48: "brouillard givrant",
            51: "bruine legere", 53: "bruine moderee", 55: "bruine dense",
            61: "pluie legere", 63: "pluie moderee", 65: "pluie forte",
            71: "neige legere", 73: "neige moderee", 75: "neige forte",
            80: "averses legeres", 81: "averses moderees", 82: "averses violentes",
            95: "orage", 96: "orage avec grele"}

def run(args):
    city = args.get("city", "Paris")
    try:
        geo_req = urllib.request.Request(
            "https://geocoding-api.open-meteo.com/v1/search?name="
            + urllib.parse.quote(city) + "&count=1&language=fr")
        with urllib.request.urlopen(geo_req, timeout=5) as r:
            geo = json.loads(r.read().decode())
        if not geo.get("results"):
            return f"Ville introuvable : {city}"
        loc = geo["results"][0]
        w_req = urllib.request.Request(
            f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}"
            f"&longitude={loc['longitude']}"
            "&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto")
        with urllib.request.urlopen(w_req, timeout=5) as r:
            weather = json.loads(r.read().decode())
        curr = weather["current"]
        desc = CODES_FR.get(curr["weather_code"], "conditions variables")
        return (f"{city} : {curr['temperature_2m']}°C, {desc}, "
                f"vent {curr['wind_speed_10m']} km/h")
    except (OSError, ValueError) as e:
        return f"Erreur meteo : {e}"
