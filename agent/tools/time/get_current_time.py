"""Outil : heure actuelle."""
import datetime

TOOL = {
    "name": "get_current_time",
    "description": "Retourne l'heure actuelle au format HH:MM.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    return datetime.datetime.now().strftime("%H:%M")
