"""Outil : créer un événement au Calendrier Apple."""

TOOL = {
    "name": "create_calendar_event",
    "description": "Crée un événement dans le calendrier Olympe (Apple Calendar).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titre de l'événement"},
            "date": {"type": "string", "description": "Date (demain, vendredi, 28/08...)"},
            "time": {"type": "string", "description": "Heure (9h30, 14:00...)"}
        },
        "required": ["title"]
    }
}

def run(args):
    from integrations.apple_calendar import create_event
    return create_event(title=args.get("title"), date=args.get("date"),
                        time=args.get("time"))
