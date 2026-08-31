"""Outil : date actuelle en français."""
import datetime

from agent.tools._helpers import date_fr

TOOL = {
    "name": "get_current_date",
    "description": "Retourne la date actuelle en français.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    return date_fr(datetime.datetime.now())
