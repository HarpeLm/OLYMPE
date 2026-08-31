"""Outil : enregistrer une note texte."""
import datetime
import re

from agent.tools._helpers import NOTES_DIR

TOOL = {
    "name": "create_note",
    "description": "Enregistre une note texte dans le dossier de notes.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titre de la note"},
            "content": {"type": "string", "description": "Contenu de la note"}
        },
        "required": ["content"]
    }
}

def run(args):
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    slug = re.sub(r"[^a-z0-9]+", "_",
                  (args.get("title") or "note").lower()).strip("_")[:30] or "note"
    fname = now.strftime("%Y-%m-%d_%H%M") + "_" + slug + ".txt"
    (NOTES_DIR / fname).write_text(args.get("content", ""), encoding="utf-8")
    return f"Note enregistree : {fname}"
