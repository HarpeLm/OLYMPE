import re
from datetime import datetime, timedelta

from integrations._core.applescript_runner import run_applescript, _as_literal
from integrations.apple_calendar._helpers import (
    CALENDAR_NAME, DAYS_FR, ensure_calendar, parse_date_fr, parse_time_fr,
)


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
                set evts to (every event of cal whose start date >= now and start date <= horizon and summary contains {_as_literal(q)})
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
