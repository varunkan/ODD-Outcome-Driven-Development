# Urgent tickets: four hours has to mean four hours

Legal went through the premium contract with the support team last week. It says, in so many words, that we answer
an urgent ticket within four hours of it reaching us. `helpdesk` does not do that: it counts the four hours in desk
time, so the clock stops whenever the desk is closed.

```python
>>> import datetime as dt
>>> from helpdesk import TicketQueue, open_ticket
>>> queue = TicketQueue()
>>> ticket = open_ticket(queue, 'Our shop is down', 'ann@example.com', dt.datetime(2026, 3, 13, 17, 0))
>>> ticket.priority, ticket.due_at
('urgent', datetime.datetime(2026, 3, 16, 11, 0))
```

That ticket came in at 17:00 on a Friday and was not due until 11:00 on the Monday, 66 hours later.

At the same meeting the on-call team raised the opposite problem. The escalation alerts go off at `due_at`, and some
of them go off when nobody is on the desk to act on them: a ticket whose target runs out exactly at closing time is
due at 18:00, when the desk has just shut. They want every due time to be a time when someone is there.

Two changes. Both are required and they go out in the same release, so please do not deliver one without the other:

1. **Urgent tickets are due within four hours, by the clock.** For every urgent ticket that `open_ticket` or
   `open_from_email` creates: `ticket.opened_at <= ticket.due_at <= ticket.opened_at + timedelta(hours=4)`.
2. **Every ticket is due while the desk is open.** For every ticket that `open_ticket` or `open_from_email` creates,
   urgent ones included: `DEFAULT_DESK.is_open(ticket.due_at)` is `True`.

Neither rule has exceptions: the contract has none, and on-call want an alert they can always act on.

What must not change: the desk's opening hours and holiday list (ops own them: `helpdesk/desk.py`,
`helpdesk/holidays.py`), how and when requests come in (`helpdesk/intake.py`: the portal, the mailbox and the
voicemail, as today), how priorities are worked out, and the targets for high, normal and low tickets beyond what
rule 2 needs. A ticket is never held back, and never given a lower priority, to make a target. The existing tests
keep passing.
