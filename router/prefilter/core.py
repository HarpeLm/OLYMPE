import re
from router.prefilter._rules import *
from router.prefilter.calendar import (
    domain_keywords_present, repair_calendar_slots, calendar_intent_hint,
)


def prefilter(text):
    """Retourne (intent_forcé, raison) si une règle matche, sinon (None, None)."""
    t = text.lower()
    for pattern, intent, reason in RULES:
        if re.search(pattern, t):
            if reason == "time_date" and re.search(r"demi[- ]heure", t):
                continue
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
                 "rendez-vous", "planning", "agenda", "réunion", "reunion",
                 "anniversaire", "dispo", "libre", "bloque", "déjeuner",
                 "diner", "dîner", "souper", "ajoute", "crée", "bloque"],
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

FOLDER_ALIAS_KEYS = ["téléchargements", "telechargements", "downloads",
                     "bureau", "desktop", "documents", "images", "photos",
                     "musique", "vidéos", "videos"]

EXT_WORDS = {"pdf": "pdf", "word": "docx", "excel": "xlsx",
             "image": "jpg", "images": "jpg", "photo": "jpg",
             "photos": "jpg", "mp3": "mp3", "vidéo": "mp4", "video": "mp4"}


def files_slots(text):
    """Extraction déterministe des slots files par regex (~0 ms)."""
    t = text.lower()
    slots = {}
    for key in FOLDER_ALIAS_KEYS:
        if key in t:
            slots["folder_name"] = key
            break
    for word, ext in EXT_WORDS.items():
        if re.search(r"\b" + word + r"\b", t):
            slots["extension"] = ext
            break
    m = re.search(r"\b(?:supprime|supprimer|efface|effacer)\s+"
                  r"(?:le\s+fichier\s+|la\s+fichier\s+|le\s+|la\s+|les\s+|mon\s+|mes\s+)?(.{2,60})$", t)
    if m:
        filename = m.group(1).strip()
        # Nettoyer "fichier" résiduel au début
        filename = re.sub(r"^fichier\s+", "", filename)
        filename = re.sub(r"^dossier\s+", "", filename)
        if filename:
            slots["filename"] = filename
    if "filename" not in slots:
        m = re.search(r"\b(?:ouvre|ouvrir|où est|ou est|où se trouve|montre|"
                      r"affiche|cherche|trouve)\s+"
                      r"(?:le\s+|la\s+|les\s+|mon\s+|ma\s+|mes\s+|moi\s+)?(.{2,60})$", t)
        if m:
            name = m.group(1).strip()
            name = re.sub(r"^(fichier|dossier)\s+", "", name)
            name = re.sub(r"\s+dans le finder$", "", name)
            if name:
                slots["filename"] = name
    if "app_name" not in slots:
        m = re.search(r"\b(?:ouvre|ouvrir|lance|lancer|ferme|fermer|quitte|quitter)\s+"
                      r"(?:le\s+|la\s+|les\s+|mon\s+|ma\s+|mes\s+|l')?(.{2,40})$", t)
        if m:
            slots["app_name"] = m.group(1).strip()
    if "filename" not in slots:
        m = re.search(r"\b(?:ferme|fermer)\s+"
                      r"(?:le\s+|la\s+|les\s+|mon\s+|ma\s+|mes\s+)?(.{2,60})$", t)
        if m:
            name = re.sub(r"^(fichier|dossier)\s+", "", m.group(1).strip())
            if name:
                slots["filename"] = name
    if "filename" not in slots:
        m = re.search(r"\b(?:duplique|dupliquer|zippe|zipper|compresse|compresser|"
                      r"décompresse|décompresser|extrais|extraire)\s+"
                      r"(?:le\s+|la\s+|les\s+|mon\s+|ma\s+|mes\s+)?(.{2,60})$", t)
        if m:
            name = re.sub(r"^(fichier|dossier)\s+", "", m.group(1).strip())
            name = re.sub(r"\s+vers\s+.*$", "", name)
            if name:
                slots["filename"] = name
    m = re.search(r"\b(?:décompresse|décompresser|extrais|extraire)\b.{0,60}\s+vers\s+(.{2,60})$", t)
    if m:
        slots["destination"] = m.group(1).strip()
    m = re.search(r"\b(?:renomme|renommer)\s+(.+?)\s+en\s+(.{2,60})$", t)
    if m:
        if "filename" not in slots:
            slots["filename"] = m.group(1).strip()
        slots["new_name"] = m.group(2).strip()
    m = re.search(r"\b(?:copie|copier)\s+(.+?)\s+vers\s+(.{2,60})$", t)
    if m:
        if "filename" not in slots:
            slots["filename"] = m.group(1).strip()
        slots["destination"] = m.group(2).strip()
    m = re.search(r"\b(?:écrase|écraser|remplace|remplacer)\s+(.+?)\s+(?:par|avec|sur)\s+(.{2,60})$", t)
    if m:
        slots["destination"] = m.group(1).strip()
        slots["source"] = m.group(2).strip()
    m = re.search(r"\b(?:tague|taguer)\s+(.+?)\s+(?:en|avec)\s+(.{2,40})$", text)
    if m:
        if "filename" not in slots:
            slots["filename"] = m.group(1).lower().strip()
        slots["tag"] = m.group(2).strip()
    m = re.search(r"\b(?:mets|mettre|passe|passer)\s+(.+?)\s+en\s+favoris\b", t)
    if m and "filename" not in slots:
        slots["filename"] = m.group(1).strip()
    m = re.search(r"^(.{2,60}?)\s+existe\b", t)
    if m and "filename" not in slots:
        slots["filename"] = re.sub(r"^(est-ce que|est-ce qu'|le fichier|le dossier)\s+", "", m.group(1).strip())
    m = re.search(r"\b(?:infos?|informations?|taille)\s+(?:de|sur|du|des|de la|de l')\s*(.{2,60})$", t)
    if m and "filename" not in slots:
        slots["filename"] = m.group(1).strip()
    return slots


INTENT_TO_FAMILY = {
    intent: fam for fam, intents in FAMILIES.items() for intent in intents
}
