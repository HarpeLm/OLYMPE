import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""
Intégrations système MJ — Palier 7
Calendrier Apple natif macOS via AppleScript (zéro API tierce).

Handlers déterministes pour le dispatcher :
  - get_next_event()
  - get_events_today()
  - create_event(title, date, time)

Les événements créés par MJ vont dans le calendrier CALENDAR_NAME
(créé automatiquement dans l'app Calendrier Apple, visible et syncable).

Test silencieux :
    python integrations/apple_calendar.py            lecture seule
    python integrations/apple_calendar.py --create   crée un événement de test
"""
import re
from datetime import datetime, timedelta
from integrations._core.applescript_runner import run_applescript, _as_literal

CALENDAR_NAME = "MJ"

DAYS_FR = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
           "vendredi": 4, "samedi": 5, "dimanche": 6}







def ensure_calendar():
    script = f'''
    tell application "Calendar"
        if not (exists calendar "{CALENDAR_NAME}") then
            make new calendar with properties {{name:"{CALENDAR_NAME}"}}
        end if
    end tell
    '''
    run_applescript(script)


def parse_date_fr(text):
    """aujourd'hui / demain / vendredi / 28/08 -> datetime.date"""
    today = datetime.now().date()
    if not text:
        return today
    t = text.strip().lower()
    if "aujourd" in t:
        return today
    if "après-demain" in t:
        return today + timedelta(days=2)
    if "demain" in t:
        return today + timedelta(days=1)
    for name, idx in DAYS_FR.items():
        if name in t:
            delta = (idx - today.weekday()) % 7 or 7
            return today + timedelta(days=delta)
    m = re.search(r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{4}))?", t)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3) or today.year)
        try:
            return datetime(y, mo, d).date()
        except ValueError:
            return today
    return today


def parse_time_fr(text):
    if not text:
        return 9, 0
    m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{2})?", text.strip().lower())
    if m:
        return int(m.group(1)), int(m.group(2) or 0)
    return 9, 0
