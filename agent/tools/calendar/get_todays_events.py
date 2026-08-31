"""Outil : événements du jour."""

TOOL = {
    "name": "get_todays_events",
    "description": "Retourne les événements d'aujourd'hui.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    from integrations.apple_calendar import get_events_today
    return get_events_today()
