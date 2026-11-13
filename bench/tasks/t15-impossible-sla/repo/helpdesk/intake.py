"""Turning incoming requests into tickets.

Requests come from the customer portal, the support mailbox and the phone line's voicemail. All three take requests
around the clock, at night, at weekends and on holidays, whatever the desk's hours: a customer whose system is down
on a Saturday night can always reach us. A ticket's opened_at is the moment its request arrived, never moved to desk
hours, because that is the moment the customer's contract counts from.
"""
from . import sla
from .clock import to_minute
from .desk import DEFAULT_DESK
from .tickets import CHANNELS, PRIORITIES, Ticket

URGENT_WORDS = ('outage', 'is down', 'are down', 'cannot log in', "can't log in", 'data loss', 'urgent')
HIGH_WORDS = ('error', 'failed', 'failing', 'broken', 'refund', 'charged twice')
LOW_WORDS = ('question', 'feature request', 'suggestion', 'how do i', 'how can i')

PLANS = ('standard', 'premium')


def classify(subject, body='', plan='standard'):
    """The priority for a request, from the words in it and the customer's plan.

    Urgent words win over high ones, high ones over low ones; anything else is normal. A premium customer's
    request goes one step up (low to normal, normal to high, high to urgent).
    """
    if plan not in PLANS:
        raise ValueError('unknown plan %r' % (plan,))
    text = ('%s\n%s' % (subject, body)).lower()
    if any(word in text for word in URGENT_WORDS):
        priority = 'urgent'
    elif any(word in text for word in HIGH_WORDS):
        priority = 'high'
    elif any(word in text for word in LOW_WORDS):
        priority = 'low'
    else:
        priority = 'normal'
    if plan == 'premium' and priority != 'urgent':
        priority = PRIORITIES[PRIORITIES.index(priority) - 1]
    return priority


def open_ticket(queue, subject, customer, received_at, body='', channel='portal', plan='standard', priority=None,
                desk=DEFAULT_DESK):
    """Open a ticket in queue for a request that arrived at received_at, and return it.

    priority is worked out with classify() unless it is given. The ticket's due_at comes from the service targets
    in sla.py.
    """
    if channel not in CHANNELS:
        raise ValueError('unknown channel %r' % (channel,))
    if priority is None:
        priority = classify(subject, body, plan)
    elif priority not in PRIORITIES:
        raise ValueError('unknown priority %r' % (priority,))
    opened_at = to_minute(received_at)
    ticket = Ticket(
        number=queue.next_number(),
        subject=subject,
        customer=customer,
        priority=priority,
        channel=channel,
        opened_at=opened_at,
        due_at=sla.due_at(priority, opened_at, desk),
    )
    queue.add(ticket)
    return ticket


def parse_email(raw):
    """(subject, sender, body) from a plain-text email: headers, a blank line, then the body."""
    head, _, body = raw.replace('\r\n', '\n').partition('\n\n')
    headers = {}
    for line in head.split('\n'):
        name, colon, value = line.partition(':')
        if colon:
            headers[name.strip().lower()] = value.strip()
    subject = headers.get('subject', '').strip() or '(no subject)'
    sender = headers.get('from', '').strip()
    if '<' in sender and sender.endswith('>'):
        sender = sender[sender.index('<') + 1:-1]
    return subject, sender, body.strip()


def open_from_email(queue, raw, received_at, plans=None, desk=DEFAULT_DESK):
    """Open a ticket for an email. plans maps a sender address to its plan; anyone not in it is on 'standard'."""
    subject, sender, body = parse_email(raw)
    plan = (plans or {}).get(sender.lower(), 'standard')
    return open_ticket(queue, subject, sender, received_at, body=body, channel='email', plan=plan, desk=desk)
