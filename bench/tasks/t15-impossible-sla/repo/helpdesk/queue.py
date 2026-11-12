"""The queue of tickets the desk works through."""
from . import sla
from .clock import to_minute
from .desk import DEFAULT_DESK


class TicketQueue:
    """Tickets by number. Numbers are handed out in order, starting after the highest number already held."""

    def __init__(self, tickets=()):
        self._tickets = {}
        for ticket in tickets:
            self.add(ticket)

    def __len__(self):
        return len(self._tickets)

    def __iter__(self):
        return iter(sorted(self._tickets.values(), key=lambda ticket: ticket.number))

    def next_number(self):
        return max(self._tickets, default=0) + 1

    def add(self, ticket):
        if ticket.number in self._tickets:
            raise ValueError('ticket #%d is already in the queue' % ticket.number)
        self._tickets[ticket.number] = ticket

    def get(self, number):
        try:
            return self._tickets[number]
        except KeyError:
            raise KeyError('no ticket #%s' % (number,)) from None

    def reply(self, number, at):
        """Record a reply sent at `at`. Only the first reply counts for the service target."""
        ticket = self.get(number)
        if ticket.status == 'closed':
            raise ValueError('ticket #%d is closed' % number)
        if to_minute(at) < ticket.opened_at:
            raise ValueError('a reply cannot come before the ticket was opened')
        if ticket.first_reply_at is None:
            ticket.first_reply_at = to_minute(at)
        ticket.status = 'replied'
        return ticket

    def close(self, number, at):
        ticket = self.get(number)
        if to_minute(at) < ticket.opened_at:
            raise ValueError('a ticket cannot be closed before it was opened')
        ticket.status = 'closed'
        ticket.closed_at = to_minute(at)
        return ticket

    def open_tickets(self):
        """Tickets not closed, the one due first at the top; equal due times by ticket number."""
        waiting = [ticket for ticket in self._tickets.values() if ticket.status != 'closed']
        return sorted(waiting, key=lambda ticket: (ticket.due_at, ticket.number))

    def awaiting_reply(self):
        return [ticket for ticket in self.open_tickets() if not ticket.replied]

    def due_within(self, now, minutes, desk=DEFAULT_DESK):
        """Unanswered tickets with at most `minutes` desk minutes left (overdue ones included): the escalation list."""
        return [ticket for ticket in self.awaiting_reply() if sla.minutes_left(ticket, now, desk) <= minutes]

    def overdue(self, now):
        return [ticket for ticket in self.awaiting_reply() if sla.is_breached(ticket, now)]
