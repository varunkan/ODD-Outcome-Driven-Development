"""Reading and writing the times stored with tickets.

Times are naive local datetimes, written to the minute as 'YYYY-MM-DD HH:MM'. Seconds are dropped on the way in, so
a ticket read back from the store compares equal to the one that was saved.
"""
import datetime as dt

FORMAT = '%Y-%m-%d %H:%M'


def to_minute(moment):
    """moment with seconds and microseconds dropped."""
    return moment.replace(second=0, microsecond=0)


def parse_time(text):
    """A datetime from 'YYYY-MM-DD HH:MM' (an ISO 'T' between date and time is accepted too)."""
    if isinstance(text, dt.datetime):
        return to_minute(text)
    if not isinstance(text, str):
        raise ValueError('a time must be text, got %r' % (text,))
    cleaned = text.strip().replace('T', ' ')
    try:
        return to_minute(dt.datetime.strptime(cleaned[:16], FORMAT))
    except ValueError:
        raise ValueError('not a time: %r (expected YYYY-MM-DD HH:MM)' % (text,)) from None


def format_time(moment):
    """'YYYY-MM-DD HH:MM' for moment, or '' for None."""
    if moment is None:
        return ''
    return moment.strftime(FORMAT)


def optional_time(text):
    """parse_time for a stored value that may be empty."""
    if text in (None, ''):
        return None
    return parse_time(text)


def minutes_between(start, end):
    """Whole clock minutes from start to end (negative when end is earlier)."""
    seconds = (end - start).total_seconds()
    return int(seconds // 60) if seconds >= 0 else -int(-seconds // 60)
