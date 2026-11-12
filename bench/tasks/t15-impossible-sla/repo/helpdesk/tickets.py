"""The ticket record."""
from .clock import format_time, optional_time, parse_time, to_minute

PRIORITIES = ('urgent', 'high', 'normal', 'low')
CHANNELS = ('portal', 'email', 'phone')
STATUSES = ('open', 'replied', 'closed')


class Ticket:
    """One customer request.

    opened_at is when the request reached us; due_at is when the first reply is due; first_reply_at and closed_at
    stay None until they happen.
    """

    __slots__ = ('number', 'subject', 'customer', 'priority', 'channel', 'opened_at', 'due_at', 'status',
                 'first_reply_at', 'closed_at')

    def __init__(self, number, subject, customer, priority, channel, opened_at, due_at, status='open',
                 first_reply_at=None, closed_at=None):
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ValueError('a ticket number is a whole number from 1, got %r' % (number,))
        if priority not in PRIORITIES:
            raise ValueError('unknown priority %r' % (priority,))
        if channel not in CHANNELS:
            raise ValueError('unknown channel %r' % (channel,))
        if status not in STATUSES:
            raise ValueError('unknown status %r' % (status,))
        if not str(subject).strip():
            raise ValueError('a ticket needs a subject')
        self.number = number
        self.subject = str(subject).strip()
        self.customer = str(customer).strip()
        self.priority = priority
        self.channel = channel
        self.opened_at = to_minute(opened_at)
        self.due_at = to_minute(due_at)
        self.status = status
        self.first_reply_at = None if first_reply_at is None else to_minute(first_reply_at)
        self.closed_at = None if closed_at is None else to_minute(closed_at)

    def __repr__(self):
        return 'Ticket(#%d %s %s, due %s)' % (self.number, self.priority, self.status, format_time(self.due_at))

    def __eq__(self, other):
        if not isinstance(other, Ticket):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    @property
    def replied(self):
        return self.first_reply_at is not None

    def to_dict(self):
        """The stored form: plain values, times as 'YYYY-MM-DD HH:MM' ('' for a time that has not happened)."""
        return {
            'number': self.number,
            'subject': self.subject,
            'customer': self.customer,
            'priority': self.priority,
            'channel': self.channel,
            'opened_at': format_time(self.opened_at),
            'due_at': format_time(self.due_at),
            'status': self.status,
            'first_reply_at': format_time(self.first_reply_at),
            'closed_at': format_time(self.closed_at),
        }

    @classmethod
    def from_dict(cls, data):
        try:
            return cls(
                number=data['number'],
                subject=data['subject'],
                customer=data.get('customer', ''),
                priority=data['priority'],
                channel=data.get('channel', 'portal'),
                opened_at=parse_time(data['opened_at']),
                due_at=parse_time(data['due_at']),
                status=data.get('status', 'open'),
                first_reply_at=optional_time(data.get('first_reply_at')),
                closed_at=optional_time(data.get('closed_at')),
            )
        except KeyError as missing:
            raise ValueError('a stored ticket has no %s' % missing) from None
