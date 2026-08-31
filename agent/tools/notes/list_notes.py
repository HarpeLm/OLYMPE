"""Outil : lister les notes récentes."""
from agent.tools._helpers import NOTES_DIR

TOOL = {
    "name": "list_notes",
    "description": "Liste les 5 notes les plus récentes.",
    "inputSchema": {"type": "object", "properties": {}, "required": []}
}

def run(args):
    if not NOTES_DIR.exists():
        return "Aucune note pour l'instant."
    files = sorted(NOTES_DIR.glob("*.txt"), reverse=True)[:5]
    if not files:
        return "Aucune note pour l'instant."
    return "Notes recentes : " + ", ".join(f.name for f in files)
