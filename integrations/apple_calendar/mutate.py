import re
from datetime import datetime, timedelta

from integrations._core.applescript_runner import run_applescript, _as_literal
from integrations.apple_calendar._helpers import (
    CALENDAR_NAME, DAYS_FR, ensure_calendar, parse_date_fr, parse_time_fr,
)


def create_event(title=None, date=None, time=None, **_):
    ensure_calendar()
    d = parse_date_fr(date)
    h, mi = parse_time_fr(time)
    title = (title or "Événement MJ").replace('"', "'").replace("\\", "")
    script = f'''
    tell application "Calendar"
        set d to current date
        set year of d to {d.year}
        set month of d to {d.month}
        set day of d to {d.day}
        set hours of d to {h}
        set minutes of d to {mi}
        set seconds of d to 0
        make new event at end of events of calendar "{CALENDAR_NAME}" with properties {{summary:{_as_literal(title)}, start date:d, end date:d + (30 * minutes)}}
    end tell
    '''
    run_applescript(script)
    return f"C'est noté : {title}, le {d.strftime('%d/%m')} à {h:02d}h{mi:02d}."


def create_recurring(title=None, date=None, recurrence=None, **_):
    ensure_calendar()
    d = parse_date_fr(date)
    freq = {"yearly": "FREQ=YEARLY", "weekly": "FREQ=WEEKLY",
            "monthly": "FREQ=MONTHLY"}.get(recurrence, "FREQ=YEARLY")
    title = (title or "Événement MJ").replace('"', "'").replace("\\", "")
    script = f'''
    tell application "Calendar"
        set d to current date
        set year of d to {d.year}
        set month of d to {d.month}
        set day of d to {d.day}
        set hours of d to 9
        set minutes of d to 0
        set seconds of d to 0
        set newEvent to make new event at end of events of calendar "{CALENDAR_NAME}" with properties {{summary:{_as_literal(title)}, start date:d, end date:d + (30 * minutes)}}
        try
            set recurrence of newEvent to "{freq}"
        end try
    end tell
    '''
    run_applescript(script)
    return f"C'est noté : {title}, récurrent ({recurrence or 'yearly'})."
