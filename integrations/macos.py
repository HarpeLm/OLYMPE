"""
Intégrations système OLYMPE — commandes macOS.

Handlers déterministes pour le dispatcher :
- open_app(app_name) : ouvre une application via open -a (SAFE)

Alias français -> nom système, pour que "ouvre la musique" marche.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


APP_ALIASES = {
    "music": "Music",
    "apple music": "Music",
    "musique": "Music",
    "ma musique": "Music",
    "safari": "Safari",
    "mail": "Mail",
    "messages": "Messages",
    "photos": "Photos",
    "notes": "Notes",
    "rappels": "Reminders",
    "reminders": "Reminders",
    "calendrier": "Calendar",
    "calendar": "Calendar",
    "finder": "Finder",
    "terminal": "Terminal",
    "plans": "Maps",
    "maps": "Maps",
    "vscode": "Visual Studio Code",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "notion": "Notion",
}


def open_app(app_name=None, **_):
    """Ouvre une application via open -a (SAFE, aucune modification)."""
    if not app_name:
        return "Quelle application ouvrir ?"
    key = app_name.lower().strip()
    target = APP_ALIASES.get(key, app_name)
    r = subprocess.run(["open", "-a", target],
                       capture_output=True, text=True, timeout=5)
    if r.returncode == 0:
        return f"Ouvert : {target}"
    return f"Je n'ai pas trouvé l'application {app_name}."


NEVER_CLOSE = {"finder"}


def _is_running(app_name):
    """Vérifie via ps si l'app tourne (aucune résolution AppleScript,
    donc aucun dialogue bloquant pour une app non installée)."""
    r = subprocess.run(["ps", "-ax", "-o", "command="],
                       capture_output=True, text=True)
    return f"{app_name}.app".lower() in r.stdout.lower()


def close_app(app_name=None, **_):
    """Ferme une application proprement (quit AppleScript, équivalent Cmd+Q)."""
    if not app_name:
        return "Quelle application fermer ?"
    key = app_name.lower().strip()
    if key in NEVER_CLOSE:
        return "Je ne ferme pas le Finder, c'est le cœur du bureau macOS."
    target = APP_ALIASES.get(key, app_name)
    if not _is_running(target):
        return f"{target} n'est pas en cours d'exécution."
    r = subprocess.run(["osascript", "-e", f'quit app "{target}"'],
                       capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        return f"Fermé : {target}"
    return f"Je n'ai pas pu fermer {app_name}."


if __name__ == "__main__":
    print(open_app("Apple Music"))
