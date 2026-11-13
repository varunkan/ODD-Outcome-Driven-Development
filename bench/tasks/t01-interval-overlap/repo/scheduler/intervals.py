"""Spans of time within one day, measured in whole minutes since midnight."""
from collections import namedtuple

MINUTES_PER_DAY = 24 * 60


class Interval(namedtuple('Interval', 'start end')):
    """The time from ``start`` up to, but not including, ``end``."""

    __slots__ = ()

    def __new__(cls, start, end):
        for value in (start, end):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError('interval bounds are whole minutes, got %r' % (value,))
        if start < 0 or end > MINUTES_PER_DAY:
            raise ValueError('interval must lie within one day')
        if end <= start:
            raise ValueError('interval must end after it starts')
        return super().__new__(cls, start, end)

    @property
    def minutes(self):
        """Length of the interval in minutes."""
        return self.end - self.start

    def __str__(self):
        return '%s-%s' % (format_time(self.start), format_time(self.end))


def parse_time(text):
    """Minutes since midnight for an 'HH:MM' string. '24:00' is accepted as the end of the day."""
    try:
        hours, minutes = text.split(':')
        hours, minutes = int(hours), int(minutes)
    except (AttributeError, ValueError):
        raise ValueError('not a time of day: %r' % (text,)) from None
    whole_day = hours == 24 and minutes == 0
    if not (0 <= minutes < 60 and (0 <= hours < 24 or whole_day)):
        raise ValueError('not a time of day: %r' % (text,))
    return hours * 60 + minutes


def format_time(minutes):
    """'HH:MM' for a number of minutes since midnight."""
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= MINUTES_PER_DAY:
        raise ValueError('not a minute of the day: %r' % (minutes,))
    return '%02d:%02d' % divmod(minutes, 60)


def overlaps(a, b):
    """True when the two intervals have time in common."""
    return a.start <= b.end and b.start <= a.end


def merge(intervals):
    """Join intervals that overlap, or follow each other without a gap, into blocks sorted by start."""
    blocks = []
    for item in sorted(intervals):
        if blocks and overlaps(blocks[-1], item):
            last = blocks[-1]
            blocks[-1] = Interval(last.start, max(last.end, item.end))
        else:
            blocks.append(item)
    return blocks


def gaps(intervals, window):
    """The free intervals left inside ``window`` once ``intervals`` are taken out, in order."""
    free = []
    cursor = window.start
    for block in merge(intervals):
        if block.end <= window.start or block.start >= window.end:
            continue
        if block.start > cursor:
            free.append(Interval(cursor, block.start))
        cursor = max(cursor, block.end)
    if cursor < window.end:
        free.append(Interval(cursor, window.end))
    return free


def total_minutes(intervals):
    """Minutes covered by the intervals, with shared time counted once."""
    return sum(block.minutes for block in merge(intervals))
