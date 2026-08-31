"""
Intégrations système OLYMPE — Palier 7
Calendrier Apple natif macOS via AppleScript (zéro API tierce).

Handlers déterministes pour le dispatcher :
  - get_next_event()
  - get_events_today()
  - create_event(title, date, time)

Les événements créés par OLYMPE vont dans le calendrier CALENDAR_NAME
(créé automatiquement dans l'app Calendrier Apple, visible et syncable).

Test silencieux :
    python integrations/apple_calendar.py            lecture seule
    python integrations/apple_calendar.py --create   crée un événement de test
"""
import re
from datetime import datetime, timedelta
from integrations._core.applescript_runner import run_applescript

CALENDAR_NAME = "Olympe"

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


def get_next_event():
    script = '''
    set now to current date
    set horizon to now + (7 * days)
    set best to missing value
    set bestSummary to ""
    set bestCal to ""
    tell application "Calendar"
        repeat with cal in calendars
            try
                set evts to (every event of cal whose start date >= now and start date <= horizon)
                repeat with e in evts
                    set s to start date of e
                    if best is missing value or s < best then
                        set best to s
                        set bestSummary to summary of e
                        set bestCal to name of cal
                    end if
                end repeat
            end try
        end repeat
    end tell
    if best is missing value then
        return "Aucun événement dans les 7 prochains jours."
    end if
    return bestSummary & ", " & (best as string) & " (" & bestCal & ")"
    '''
    return run_applescript(script)


def get_events_today():
    script = '''
    set now to current date
    set time of now to 0
    set tomorrow to now + (1 * days)
    set eventList to {}
    tell application "Calendar"
        repeat with cal in calendars
            try
                set evts to (every event of cal whose start date >= now and start date < tomorrow)
                repeat with e in evts
                    set end of eventList to (summary of e & " à " & (start date of e as string))
                end repeat
            end try
        end repeat
    end tell
    if (count of eventList) is 0 then
        return "Aucun événement aujourd'hui."
    end if
    set AppleScript's text item delimiters to linefeed
    return eventList as string
    '''
    return run_applescript(script)


def create_event(title=None, date=None, time=None, **_):
    ensure_calendar()
    d = parse_date_fr(date)
    h, mi = parse_time_fr(time)
    title = (title or "Événement OLYMPE").replace('"', "'").replace("\\", "")
    script = f'''
    tell application "Calendar"
        set d to current date
        set year of d to {d.year}
        set month of d to {d.month}
        set day of d to {d.day}
        set hours of d to {h}
        set minutes of d to {mi}
        set seconds of d to 0
        make new event at end of events of calendar "{CALENDAR_NAME}" with properties {{summary:"{title}", start date:d, end date:d + (30 * minutes)}}
    end tell
    '''
    run_applescript(script)
    return f"C'est noté : {title}, le {d.strftime('%d/%m')} à {h:02d}h{mi:02d}."


if __name__ == "__main__":
    import sys
    print("Prochain événement :", get_next_event())
    print()
    print("Aujourd'hui :")
    print(get_events_today())
    if "--create" in sys.argv:
        print()
        print(create_event(title="Test OLYMPE", date="demain", time="9h00"))
        print("Vérifie dans l'app Calendrier : calendrier 'Olympe'.")


def next_event(**_):
    return get_next_event()


def events_today(**_):
    return get_events_today()


def events_date(date=None, **_):
    d = parse_date_fr(date)
    script = f'''
    tell application "Calendar"
        set target to current date
        set year of target to {d.year}
        set month of target to {d.month}
        set day of target to {d.day}
        set time of target to 0
        set next_day to target + (1 * days)
        set eventList to {{}}
        repeat with cal in calendars
            try
                set evts to (every event of cal whose start date >= target and start date < next_day)
                repeat with e in evts
                    set end of eventList to (summary of e & " à " & (start date of e as string))
                end repeat
            end try
        end repeat
        if (count of eventList) is 0 then
            return "Aucun événement le {d.strftime('%d/%m')}."
        end if
        set AppleScript's text item delimiters to linefeed
        return eventList as string
    end tell
    '''
    return run_applescript(script)


def check_availability(date=None, time=None, duration_minutes=None, **_):
    d = parse_date_fr(date)
    h, mi = parse_time_fr(time)
    dur = int(duration_minutes or 60)
    script = f'''
    tell application "Calendar"
        set target to current date
        set year of target to {d.year}
        set month of target to {d.month}
        set day of target to {d.day}
        set hours of target to {h}
        set minutes of target to {mi}
        set seconds of target to 0
        set endW to target + ({dur} * minutes)
        repeat with cal in calendars
            try
                set evts to (every event of cal whose start date < endW and end date > target)
                if (count of evts) > 0 then
                    set e to item 1 of evts
                    return "Pas libre : " & (summary of e) & " à " & (start date of e as string)
                end if
            end try
        end repeat
    end tell
    return "Oui, tu es libre à ce moment-là."
    '''
    return run_applescript(script)


def search(query=None, **_):
    q = (query or "").replace('"', "'")
    script = f'''
    set now to current date
    set horizon to now + (30 * days)
    set eventList to {{}}
    tell application "Calendar"
        repeat with cal in calendars
            try
                set evts to (every event of cal whose start date >= now and start date <= horizon and summary contains "{q}")
                repeat with e in evts
                    set end of eventList to (summary of e & " le " & (start date of e as string))
                end repeat
            end try
        end repeat
    end tell
    if (count of eventList) is 0 then
        return "Aucun événement trouvé pour cette recherche dans les 30 prochains jours."
    end if
    set AppleScript's text item delimiters to linefeed
    return eventList as string
    '''
    return run_applescript(script)


def create_recurring(title=None, date=None, recurrence=None, **_):
    ensure_calendar()
    d = parse_date_fr(date)
    freq = {"yearly": "FREQ=YEARLY", "weekly": "FREQ=WEEKLY",
            "monthly": "FREQ=MONTHLY"}.get(recurrence, "FREQ=YEARLY")
    title = (title or "Événement OLYMPE").replace('"', "'").replace("\\", "")
    script = f'''
    tell application "Calendar"
        set d to current date
        set year of d to {d.year}
        set month of d to {d.month}
        set day of d to {d.day}
        set hours of d to 9
        set minutes of d to 0
        set seconds of d to 0
        set newEvent to make new event at end of events of calendar "{CALENDAR_NAME}" with properties {{summary:"{title}", start date:d, end date:d + (30 * minutes)}}
        try
            set recurrence of newEvent to "{freq}"
        end try
    end tell
    '''
    run_applescript(script)
    return f"C'est noté : {title}, récurrent ({recurrence or 'yearly'})."
