"""Package Calendrier — re-export paresseux (compatibilite imports)."""

_EXPORTS = {
    "ensure_calendar": "_helpers",
    "parse_date_fr": "_helpers",
    "parse_time_fr": "_helpers",
    "get_next_event": "query",
    "get_events_today": "query",
    "next_event": "query",
    "events_today": "query",
    "events_date": "query",
    "check_availability": "query",
    "search": "query",
    "create_event": "mutate",
    "create_recurring": "mutate",
    "CALENDAR_NAME": "_helpers",
    "DAYS_FR": "_helpers",
}

def __getattr__(name):
    if name in _EXPORTS:
        import importlib
        m = importlib.import_module(f"integrations.apple_calendar.{_EXPORTS[name]}")
        return getattr(m, name)
    raise AttributeError(name)
