"""The weekly service report: per priority, how many tickets came in, how many missed their target."""
from . import sla
from .clock import format_time
from .desk import DEFAULT_DESK
from .tickets import PRIORITIES


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def service_report(tickets, start, end, now, desk=DEFAULT_DESK):
    """Figures for the tickets opened from start up to, not including, end, as they stand at now.

    Returns {priority: {'opened', 'replied', 'breached', 'median_reply_minutes'}} for every priority, plus
    'period': (start, end). Reply times are in desk minutes; the median is None when nothing was answered.
    """
    if end <= start:
        raise ValueError('the period must end after it starts')
    rows = {}
    for priority in PRIORITIES:
        chosen = [ticket for ticket in tickets if ticket.priority == priority and start <= ticket.opened_at < end]
        waits = [sla.first_reply_minutes(ticket, desk) for ticket in chosen if ticket.replied]
        rows[priority] = {
            'opened': len(chosen),
            'replied': len(waits),
            'breached': sum(1 for ticket in chosen if sla.is_breached(ticket, now)),
            'median_reply_minutes': _median(waits),
        }
    rows['period'] = (start, end)
    return rows


def format_report(report):
    """The report as a text table."""
    start, end = report['period']
    lines = ['Service report %s to %s' % (format_time(start), format_time(end)),
             '%-8s %7s %8s %9s %13s' % ('priority', 'opened', 'replied', 'breached', 'median reply')]
    for priority in PRIORITIES:
        row = report[priority]
        median = row['median_reply_minutes']
        lines.append('%-8s %7d %8d %9d %13s' % (
            priority, row['opened'], row['replied'], row['breached'], '-' if median is None else '%g min' % median))
    return '\n'.join(lines) + '\n'
