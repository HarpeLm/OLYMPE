"""Dispatcher généraliste reconstruit pour le pipeline vocal.

Combine trois briques existantes :
- router.dispatcher.dispatch : volets (v5, déterministe)
- router.prefilter.prefilter : règles regex ~0 ms (fichiers, apps...)
- router/intents.yaml        : mapping intent -> handler déterministe

Fournit l'objet Dispatcher attendu par le pipeline :
.route(text) -> dict(intent/action/confidence/slots/handler) et .schemas.
"""
import importlib.util
import re
from pathlib import Path

import yaml

from router.dispatcher import dispatch as dispatch_shutters
from router.prefilter import prefilter, files_slots

ROOT = Path(__file__).resolve().parents[1]
INTENTS_PATH = ROOT / "router" / "intents.yaml"

# Intents volets (dispatcher v5) -> handler exécutable
SHUTTER_HANDLERS = {
    "shutters.open": "integrations/tahoma.py::open_shutter",
    "shutters.close": "integrations/tahoma.py::close_shutter",
    "shutters.set_position": "integrations/tahoma.py::set_shutter_position",
    "shutters.open_all": "agent/tools/shutters/open_all_shutters.py::run",
    "shutters.close_all": "agent/tools/shutters/close_all_shutters.py::run",
    "shutters.list": "agent/tools/shutters/list_shutters.py::run",
}

# Chemins d'handlers périmés dans intents.yaml -> chemins réels
_HANDLER_FIXES = {
    "integrations/calendar.py::": "integrations/apple_calendar.py::",
}
# Questions factuelles -> web_search OBLIGATOIRE (anti-hallucination)
WEB_RE = re.compile(
    r"cherche(r|z)?\s+(sur|dans|en ligne)|sur (inter|le )net|sur internet|"
    r"qui a (gagn|remport)\w+|qui (gagne|remporte)|actualit\w+|"
    r"derni[èe]res? news|tour de france|coupe du monde|jeux olympiques", re.I)



def _module_exists(handler):
    if not handler or "::" not in handler:
        return False
    mod = handler.split("::", 1)[0].replace("/", ".").removesuffix(".py")
    return importlib.util.find_spec(mod) is not None


def _load_schemas():
    with open(INTENTS_PATH, "r", encoding="utf-8") as f:
        taxo = yaml.safe_load(f) or {}
    schemas = {}
    for entry in taxo.get("deterministic_intents", []):
        entry = dict(entry)
        handler = entry.get("handler", "")
        for old, new in _HANDLER_FIXES.items():
            handler = handler.replace(old, new)
        entry["handler"] = handler
        schemas[entry["name"]] = entry
    return schemas


class Dispatcher:
    """Adaptateur de routage : volets + préfiltre + taxonomie yaml."""

    def __init__(self):
        self.schemas = _load_schemas()

    def route(self, text):
        # 1. Volets (dispatcher v5)
        res = dispatch_shutters(text)
        if res is not None:
            d = res.to_dict()
            d["action"] = "deterministic"
            d["handler"] = SHUTTER_HANDLERS.get(res.intent)
            return d

        # 1b. Fait récent -> web_search obligatoire (jamais de mémoire)
        if WEB_RE.search(text):
            return {"intent": "web_search", "action": "deterministic",
                    "confidence": 0.9, "slots": {"query": text},
                    "handler": None}

        # 2. Préfiltre règles (fichiers, apps...)
        forced, domain = prefilter(text)
        if forced and forced != "fallback" and forced in self.schemas:
            handler = self.schemas[forced].get("handler")
            if _module_exists(handler):
                slots = files_slots(text) if domain.startswith("files") else {}
                return {"intent": forced, "action": "deterministic",
                        "confidence": 0.9, "slots": slots, "handler": handler}

        # 3. Fallback vers le LLM + outils
        return {"intent": forced or "fallback", "action": "fallback",
                "confidence": 0.0, "slots": {}}
