"""Outil : prochain événement (7 jours)."""

TOOL = {
    "name": "get_next_calendar_event",
    "description": "Retourne le prochain événement des 7 prochains jours.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    from integrations.apple_calendar import get_next_event
    return get_next_event()
