"""Booked time is kept as whole minutes."""

MINUTES_PER_HOUR = 60


def total_minutes(entries):
    """The sum of a list of bookings, each a whole number of minutes (0 or more)."""
    total = 0
    for minutes in entries:
        if not isinstance(minutes, int) or minutes < 0:
            raise ValueError('a booking is a whole number of minutes, 0 or more: %r' % (minutes,))
        total += minutes
    return total


def format_minutes(minutes):
    """165 -> '2h 45m'; 120 -> '2h'; 45 -> '45m'; 0 -> '0m'."""
    hours, rest = divmod(minutes, MINUTES_PER_HOUR)
    if hours and rest:
        return '%dh %dm' % (hours, rest)
    if hours:
        return '%dh' % hours
    return '%dm' % rest
