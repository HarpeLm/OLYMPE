"""Helpers partages pour les outils (non auto-decouvert : prefixe _)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NOTES_DIR = ROOT / "data" / "notes"

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
           "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]

def date_fr(dt):
    return f"{JOURS_FR[dt.weekday()]} {dt.day} {MOIS_FR[dt.month - 1]} {dt.year}"
