"""
Pré-filtre règles/regex (~0 ms) — roadmap §4 [1]
Court-circuite le dispatcheur pour les motifs évidents.
"""
import re

RULES = [
    # Heure/date → fallback (aucun intent dédié ; le LLM + outil MCP répond)
    (r"\b(heure|quel jour|quelle date|on est le|quelle heure)\b", "fallback", "time_date"),
    # Météo → get_weather forcé (l'intent existe, le modèle se trompe)
    (r"\b(météo|temps fait-il|pleut|neige|température)\b", "get_weather", "weather"),
    # Minuteur/timer → fallback (aucun intent dédié)
    (r"\b(minuteur|timer|compte à rebours|alarme dans)\b", "fallback", "timer"),
]

def prefilter(text):
    """Retourne (intent_forcé, raison) si une règle matche, sinon (None, None)."""
    t = text.lower()
    for pattern, intent, reason in RULES:
        if re.search(pattern, t):
            return intent, reason
    return None, None


FAMILIES = {
    "music": {"play_music", "pause_music", "resume_music", "next_track",
              "previous_track", "get_now_playing", "sleep_timer", "repeat_track"},
    "calendar": {"create_event", "create_recurring_event", "get_next_event",
                 "get_events_today", "get_events_date", "check_availability",
                 "search_events"},
    "files": {"find_file", "search_content", "open_file", "open_folder",
              "list_recent_files"},
    "macos": {"open_app", "close_app", "set_volume", "set_brightness",
              "take_screenshot", "sleep_mac", "toggle_wifi", "toggle_bluetooth",
              "run_shortcut", "get_wifi_status", "toggle_airdrop"},
    "weather": {"get_weather"},
}

KEYWORDS = {
    "music": ["musique", "chanson", "playlist", "piste", "album", "artiste",
              "joue", "jouer", "pause", "reprend", "suivant", "précédent",
              "precedent", "écoute", "ecoute", "répète", "repeat"],
    "calendar": ["calendrier", "événement", "evenement", "rendez", "rdv",
                 "planning", "agenda", "réunion", "reunion", "anniversaire",
                 "dispo", "libre", "bloque"],
    "files": ["fichier", "dossier", "document", "pdf", "téléchargement",
              "telechargement", "récent", "recent", "ouvre", "ouvrir",
              "contenu", "cherche", "trouve", "liste"],
    "macos": ["ouvre", "lance", "application", "appli", "volume", "luminosité",
              "luminosite", "capture", "écran", "ecran", "veille", "wifi",
              "bluetooth", "airdrop", "raccourci", "ferme", "quitte", "allume",
              "éteins", "active", "coupe", "désactive"],
    "weather": ["météo", "meteo", "temps", "pleut", "neige", "température",
                "temperature", "degrés", "degres"],
}

INTENT_TO_FAMILY = {
    intent: fam for fam, intents in FAMILIES.items() for intent in intents
}


def domain_keywords_present(intent, text):
    fam = INTENT_TO_FAMILY.get(intent)
    if fam is None:
        return True
    t = text.lower()
    return any(k in t for k in KEYWORDS[fam])


EXTRA_ALIASES = {
    "search_files": "find_file",
    "list_files": "list_recent_files",
    "increase_brightness": "set_brightness",
    "decrease_brightness": "set_brightness",
    "search_facture": "search_content",
    "add_food": "create_event",
    "quit_app": "close_app",
    "check_wifi": "get_wifi_status",
}
