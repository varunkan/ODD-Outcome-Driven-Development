# helpdesk

The support desk's ticket system: requests come in, get a priority and a due time for the first reply, and the desk
works through the queue. Python 3 standard library only.

```python
import datetime as dt
from helpdesk import TicketQueue, open_ticket

queue = TicketQueue()
ticket = open_ticket(queue, 'Payment failed', 'ann@example.com', dt.datetime(2026, 3, 9, 13, 0))
ticket.priority     # 'high'
ticket.due_at       # datetime(2026, 3, 10, 11, 0): eight desk hours later
```

## What is in it

- `helpdesk/desk.py`: when the desk is staffed (`Desk`, `DEFAULT_DESK`): `is_open`, `next_open`,
  `add_working_minutes`, `working_minutes_between`. Ops own the hours; the holiday list is in `holidays.py`.
- `helpdesk/intake.py`: `open_ticket`, `open_from_email` and `classify` (the priority, from the words of the
  request and the customer's plan).
- `helpdesk/sla.py`: the service targets per priority and `due_at`, `minutes_left`, `is_breached`.
- `helpdesk/queue.py`: `TicketQueue`: replies, closing, the open list, the escalation list (`due_within`).
- `helpdesk/store.py`: the queue saved as JSON lines.
- `helpdesk/report.py`: the weekly service report.

Times are naive local datetimes, kept to the minute.

## Service targets

| priority | first reply within |
|---|---|
| urgent | 4 desk hours |
| high | 8 desk hours |
| normal | 2 desk days |
| low | 5 desk days |

## Tests

```
python3 -m unittest discover -s tests
```
