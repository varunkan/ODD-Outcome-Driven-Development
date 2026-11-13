"""One day's bookings for a single room."""
from collections import namedtuple

from .intervals import Interval, format_time, gaps, merge, overlaps, parse_time


class BookingConflict(Exception):
    """Raised when a new booking would clash with bookings already made."""

    def __init__(self, clashes):
        self.clashes = list(clashes)
        super().__init__('clashes with: ' + ', '.join(booking.title for booking in self.clashes))


class Booking(namedtuple('Booking', 'title interval')):
    """A titled interval. ``start`` and ``end`` give the times as 'HH:MM'."""

    __slots__ = ()

    @property
    def start(self):
        return format_time(self.interval.start)

    @property
    def end(self):
        return format_time(self.interval.end)


class Schedule:
    """Bookings for one room on one day, between opening and closing time."""

    def __init__(self, opens='08:00', closes='18:00'):
        self._hours = Interval(parse_time(opens), parse_time(closes))
        self._bookings = []

    def book(self, title, start, end):
        """Add a booking and return it. ``start`` and ``end`` are 'HH:MM' strings."""
        slot = Interval(parse_time(start), parse_time(end))
        if slot.start < self._hours.start or slot.end > self._hours.end:
            raise ValueError('booking must lie within opening hours %s' % (self._hours,))
        clashes = self._clashes(slot)
        if clashes:
            raise BookingConflict(clashes)
        booking = Booking(title, slot)
        self._bookings.append(booking)
        self._bookings.sort(key=lambda made: made.interval)
        return booking

    def cancel(self, title):
        """Remove every booking with this title. Returns how many were removed."""
        kept = [booking for booking in self._bookings if booking.title != title]
        removed = len(self._bookings) - len(kept)
        self._bookings = kept
        return removed

    def bookings(self):
        """All bookings, earliest first."""
        return list(self._bookings)

    def conflicts(self, start, end):
        """The bookings that clash with the given times, earliest first."""
        return self._clashes(Interval(parse_time(start), parse_time(end)))

    def busy_blocks(self):
        """Booked time as ('HH:MM', 'HH:MM') pairs, with bookings that run into each other joined."""
        return [(format_time(block.start), format_time(block.end)) for block in merge(self._taken())]

    def free_slots(self, minimum=1):
        """Unbooked time inside opening hours as ('HH:MM', 'HH:MM') pairs of at least ``minimum`` minutes."""
        return [(format_time(gap.start), format_time(gap.end))
                for gap in gaps(self._taken(), self._hours) if gap.minutes >= minimum]

    def first_free(self, minutes, after=None):
        """The earliest free ('HH:MM', 'HH:MM') slot of ``minutes`` minutes, or None when there is none.

        ``after`` ('HH:MM') skips any time before it.
        """
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError('slot length must be a positive number of minutes')
        earliest = parse_time(after) if after is not None else self._hours.start
        for gap in gaps(self._taken(), self._hours):
            start = max(gap.start, earliest)
            if start + minutes <= gap.end:
                return format_time(start), format_time(start + minutes)
        return None

    def _taken(self):
        return [booking.interval for booking in self._bookings]

    def _clashes(self, slot):
        return [booking for booking in self._bookings if overlaps(slot, booking.interval)]
