"""Days the support desk stays shut although they fall on a weekday.

Ops keep this list. It is written as ISO dates so it can be pasted from the HR calendar as it stands.
"""
import datetime as dt

_LISTED = """
2026-01-01  New Year's Day
2026-04-03  Good Friday
2026-04-06  Easter Monday
2026-05-04  Early May bank holiday
2026-05-25  Spring bank holiday
2026-08-31  Summer bank holiday
2026-12-25  Christmas Day
2026-12-28  Boxing Day (substitute day)
2027-01-01  New Year's Day
2027-03-26  Good Friday
2027-03-29  Easter Monday
2027-05-03  Early May bank holiday
2027-05-31  Spring bank holiday
2027-08-30  Summer bank holiday
2027-12-27  Christmas Day (substitute day)
2027-12-28  Boxing Day (substitute day)
"""


def parse_holidays(text):
    """The dates in text: one per line, an ISO date first, then anything (the name of the day). '#' starts a comment."""
    days = set()
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        first = line.split()[0]
        try:
            days.add(dt.date.fromisoformat(first))
        except ValueError:
            raise ValueError('line %d: not an ISO date: %r' % (number, first)) from None
    return frozenset(days)


HOLIDAYS = parse_holidays(_LISTED)
