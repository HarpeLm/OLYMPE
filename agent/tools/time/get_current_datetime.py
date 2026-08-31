"""Outil : date et heure complètes en français."""
import datetime

from agent.tools._helpers import date_fr

TOOL = {
    "name": "get_current_datetime",
    "description": "Retourne la date et l'heure complètes en français.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    now = datetime.datetime.now()
    return f"{date_fr(now)}, {now.strftime('%H:%M:%S')}"
