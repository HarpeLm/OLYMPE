"""Outil : minuteur avec annonce vocale."""
import re
import subprocess

TOOL = {
    "name": "set_timer",
    "description": "Démarre un minuteur. Une voix prévient à la fin.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "duration_minutes": {"type": "integer", "description": "Durée en minutes"},
            "duration_seconds": {"type": "integer", "description": "Durée en secondes"},
            "label": {"type": "string", "description": "Nom du minuteur"}
        },
        "required": []
    }
}

def run(args):
    minutes = int(args.get("duration_minutes", 0) or 0)
    seconds = int(args.get("duration_seconds", 0) or 0) or minutes * 60
    label = re.sub(r"[^a-zA-Z0-9 àéèêç-]", "", args.get("label", "Minuteur"))
    if seconds <= 0:
        return "Durée invalide."
    cmd = f"sleep {seconds} && (say -v Thomas 'Minuteur {label} termine' || say 'Minuteur {label} termine')"
    subprocess.Popen(
        ["bash", "-c", cmd],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    duree = f"{minutes} minutes" if minutes else f"{seconds} secondes"
    return f"{label} demarre pour {duree}. Une voix te prevenir a la fin."
