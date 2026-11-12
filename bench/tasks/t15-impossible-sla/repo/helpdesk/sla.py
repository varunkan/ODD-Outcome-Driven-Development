"""Service targets: how soon each ticket must get its first reply.

Targets are counted in desk time (see desk.py): the clock stops while the desk is closed.
"""
from .desk import DEFAULT_DESK

# Desk minutes from opening to the first reply. The desk is open ten hours a day, so 1200 minutes is two desk days.
TARGETS = {
    'urgent': 240,
    'high': 480,
    'normal': 1200,
    'low': 3000,
}


def target_minutes(priority):
    """The target for priority, in desk minutes."""
    try:
        return TARGETS[priority]
    except KeyError:
        raise ValueError('unknown priority %r' % (priority,)) from None


def due_at(priority, opened_at, desk=DEFAULT_DESK):
    """When the first reply to a ticket of this priority, opened at opened_at, is due."""
    return desk.add_working_minutes(opened_at, target_minutes(priority))


def minutes_left(ticket, now, desk=DEFAULT_DESK):
    """Desk minutes from now until the ticket is due: negative once it is overdue, None once it has been answered."""
    if ticket.replied:
        return None
    if now <= ticket.due_at:
        return desk.working_minutes_between(now, ticket.due_at)
    return -desk.working_minutes_between(ticket.due_at, now)


def is_breached(ticket, now):
    """True when the first reply came after due_at, or has not come and now is past due_at."""
    if ticket.replied:
        return ticket.first_reply_at > ticket.due_at
    return now > ticket.due_at


def first_reply_minutes(ticket, desk=DEFAULT_DESK):
    """Desk minutes the customer waited for the first reply, or None before it."""
    if not ticket.replied:
        return None
    return desk.working_minutes_between(ticket.opened_at, ticket.first_reply_at)
