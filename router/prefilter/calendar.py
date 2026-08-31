import re
from router.prefilter._rules import *


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


def repair_calendar_slots(text, slots):
    """Complète déterministement les slots calendrier manquants."""
    import re
    slots = dict(slots or {})
    t = text.strip()
    if not slots.get("date"):
        m = re.search(r"(aujourd'hui|après-demain|demain|lundi|mardi|mercredi|"
                      r"jeudi|vendredi|samedi|dimanche|\d{1,2}/\d{1,2}(?:/\d{4})?)",
                      t, re.I)
        slots["date"] = m.group(1).lower() if m else "aujourd'hui"
    if not slots.get("time"):
        m = re.search(r"\b(\d{1,2})\s*[h:]\s*(\d{2})?\b", t)
        if m:
            slots["time"] = f"{m.group(1)}h{m.group(2) or '00'}"
        elif re.search(r"\bmidi\b", t, re.I):
            slots["time"] = "12h00"
        elif re.search(r"\bminuit\b", t, re.I):
            slots["time"] = "00h00"
    if not slots.get("title"):
        title = t
        title = re.sub(r"^(ajoute|ajoutez|crée|créez|créer|bloque|bloquer|mets|"
                       r"met|note|planifie)\s+", "", title, flags=re.I)
        title = re.sub(r"(aujourd'hui|après-demain|demain|lundi|mardi|mercredi|"
                       r"jeudi|vendredi|samedi|dimanche)", " ", title, flags=re.I)
        title = re.sub(r"\d{1,2}/\d{1,2}(?:/\d{4})?", " ", title)
        title = re.sub(r"(?:\s+(?:à|a))?\s*\d{1,2}\s*[h:]\s*\d{0,2}", " ", title, flags=re.I)
        title = re.sub(r"\b(à|a)\s+(midi|minuit)\b", " ", title, flags=re.I)
        title = re.sub(r"^(un|une|le|la|les|mon|ma|mes)\s+", "", title, flags=re.I)
        title = re.sub(r"\s+", " ", title).strip(" .,")
        title = re.sub(r"(\s|^)(à|a|de|du|des|le|la|les|un|une|pour)+$", "", title, flags=re.I).strip()
        if title:
            slots["title"] = title
    return slots


def calendar_intent_hint(text):
    """Intent calendrier déterministe sur marqueurs forts (sinon None)."""
    import re
    t = text.lower()
    if re.search(r"\b(libre|dispo|disponible)\b", t):
        return "check_availability"
    if re.search(r"\b(ajoute|ajoutez|crée|créez|créer|bloque|bloquer|planifie|planifier)\b", t) and \
       re.search(r"(réunion|reunion|rendez|déjeuner|dejeuner|dîner|diner|"
                 r"événement|evenement|appel|travail|anniversaire|rdv)", t):
        return "create_event"
    if re.search(r"\b(agenda|planning|calendrier)\b", t):
        if re.search(r"(prochain|prochaine|suit|suivant)", t):
            return "get_next_event"
        if "aujourd" in t:
            return "get_events_today"
        return "get_events_date"
    if re.search(r"\b(cherche|retrouve)\b", t) and \
       re.search(r"(événement|evenement|rendez|réunion|reunion)", t):
        return "search_events"
    return None
