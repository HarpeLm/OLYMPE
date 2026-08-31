"""Package prefilter — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "prefilter": "core",
    "files_slots": "core",
    "domain_keywords_present": "calendar",
    "repair_calendar_slots": "calendar",
    "calendar_intent_hint": "calendar",
    "RULES": "_rules",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"router.prefilter.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
